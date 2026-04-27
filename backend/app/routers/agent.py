from app.config import get_settings
from app.models import ClassifiedBug, RunAgentRequest, SSEEventType, TestCase, TestResult
from app.tools import (
    classify_bug,
    crawl_app,
    execute_test,
    generate_report,
    generate_test_cases,
    reflect_and_expand,
    suggest_fix,
)
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import logging
import os
import time
from datetime import datetime
from typing import AsyncGenerator

router = APIRouter(tags=["agent"])
settings = get_settings()
_last_run_cache: dict = {}
logger = logging.getLogger(__name__)


def make_event(type: SSEEventType, step: str, payload) -> str:
    event = {
        "type": type.value,
        "step": step,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return f"data: {json.dumps(event)}\n\n"


@router.post("/run-agent")
async def run_agent(request: RunAgentRequest) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        import glob as _glob

        old_shots = _glob.glob(os.path.join(settings.screenshot_dir, "*.png"))
        for f in old_shots:
            try:
                os.remove(f)
            except Exception:
                pass

        try:
            url = request.url.strip()

            pipeline_start = time.time()
            # ── STEP 1: CRAWL ──────────────────────────────────────────────
            yield make_event(SSEEventType.agent_thought, "crawl_app", f"Starting crawl of {url}...")
            yield make_event(SSEEventType.tool_call, "crawl_app", {"url": url})
            sitemap = await crawl_app(url)
            total_elements = sum(len(p.elements) for p in sitemap.pages)
            yield make_event(SSEEventType.tool_result, "crawl_app", {
                "pages_found": len(sitemap.pages),
                "total_elements": total_elements,
                "pages": [{"url": p.url, "title": p.title, "element_count": len(p.elements)} for p in sitemap.pages]
            })
            yield make_event(SSEEventType.agent_thought, "crawl_app",
                f"Crawl complete. Found {len(sitemap.pages)} page(s) and {total_elements} interactive elements.")

            # ── STEP 2: GENERATE TEST CASES ────────────────────────────────
            yield make_event(SSEEventType.agent_thought, "generate_test_cases",
                "Analysing sitemap and generating test cases with Gemini...")
            yield make_event(SSEEventType.tool_call, "generate_test_cases",
                {"pages": len(sitemap.pages), "elements": total_elements, "model": settings.gemini_model})
            test_cases = await generate_test_cases(sitemap)
            yield make_event(SSEEventType.tool_result, "generate_test_cases", {
                "count": len(test_cases),
                "test_cases": [{"id": tc.id, "title": tc.title, "type": tc.type} for tc in test_cases]
            })
            type_coverage = ", ".join(sorted(set(tc.type for tc in test_cases)))
            yield make_event(SSEEventType.agent_thought, "generate_test_cases",
                f"Generated {len(test_cases)} test cases covering: {type_coverage}.")

            # ── STEP 3: EXECUTE TESTS ──────────────────────────────────────
            all_results: list[TestResult] = []
            all_bugs: list[ClassifiedBug] = []
            failed_pairs: list[tuple[TestCase, TestResult]] = []
            tested_flows: list[str] = []

            yield make_event(SSEEventType.agent_thought, "execute_test",
                f"Executing {len(test_cases)} test cases in headless browser...")

            for i, tc in enumerate(test_cases):
                yield make_event(SSEEventType.tool_call, "execute_test", {
                    "test_id": tc.id,
                    "title": tc.title,
                    "type": tc.type,
                    "progress": f"{i+1}/{len(test_cases)}"
                })
                result = await execute_test(tc, url, settings.screenshot_dir)
                all_results.append(result)
                tested_flows.append(tc.title)
                if not result.passed:
                    failed_pairs.append((tc, result))
                yield make_event(SSEEventType.tool_result, "execute_test", {
                    "test_id": result.test_id,
                    "passed": result.passed,
                    "duration_ms": result.duration_ms,
                    "error_message": result.error_message,
                    "screenshot_path": result.screenshot_path
                })

            passed_count = sum(1 for r in all_results if r.passed)
            failed_count = len(all_results) - passed_count
            yield make_event(SSEEventType.agent_thought, "execute_test",
                f"Execution complete. {passed_count} passed, {failed_count} failed.")

            # ── STEP 4: CLASSIFY BUGS ──────────────────────────────────────
            if failed_pairs:
                yield make_event(SSEEventType.agent_thought, "classify_bug",
                    f"Classifying {len(failed_pairs)} failure(s) with Gemini...")
                for tc, result in failed_pairs:
                    yield make_event(SSEEventType.tool_call, "classify_bug", {
                        "test_id": result.test_id,
                        "title": tc.title,
                        "error_preview": (result.error_message or "")[:120]
                    })
                    bug = await classify_bug(tc, result)

                    # Skip false positives — never add to report
                    if bug.severity.value == "false_positive" or \
                       "false positive" in bug.root_cause_hypothesis.lower():
                        logger.info("Skipping false positive: %s", bug.title)
                        yield make_event(SSEEventType.agent_thought, "classify_bug",
                            f"Skipping false positive: '{bug.title[:50]}' — element appears to be working as designed.")
                        continue  # don't add to all_bugs, don't call suggest_fix

                    # Generate fix suggestion for Critical and Major bugs only
                    if bug.severity.value in ("Critical", "Major"):
                        yield make_event(SSEEventType.agent_thought, "suggest_fix",
                            f"Generating fix suggestion for {bug.severity.value} bug: {bug.title[:50]}...")
                        
                        yield make_event(SSEEventType.tool_call, "suggest_fix", {
                            "test_id": bug.test_id,
                            "severity": bug.severity.value,
                            "title": bug.title
                        })

                        fix = await suggest_fix(bug, tc)
                        bug.fix_suggestion = fix

                        yield make_event(SSEEventType.tool_result, "suggest_fix", {
                            "test_id": bug.test_id,
                            "fix_suggestion": fix[:150] + "..." if len(fix) > 150 else fix
                        })

                    all_bugs.append(bug)
                    yield make_event(SSEEventType.tool_result, "classify_bug", {
                        "test_id": bug.test_id,
                        "severity": bug.severity.value,
                        "title": bug.title,
                        "root_cause_hypothesis": bug.root_cause_hypothesis,
                        "screenshot_path": bug.screenshot_path,
                        "has_fix_suggestion": bug.fix_suggestion is not None
                    })
                critical_n = sum(1 for b in all_bugs if b.severity.value == "Critical")
                major_n = sum(1 for b in all_bugs if b.severity.value == "Major")
                minor_n = sum(1 for b in all_bugs if b.severity.value == "Minor")
                yield make_event(SSEEventType.agent_thought, "classify_bug",
                    f"Classification complete. {critical_n} Critical, {major_n} Major, {minor_n} Minor. "
                    f"Fix suggestions generated for {critical_n + major_n} bugs.")
            else:
                yield make_event(SSEEventType.agent_thought, "classify_bug",
                    "All tests passed — no bugs to classify.")

            # ── STEP 5: REFLECT AND EXPAND ─────────────────────────────────
            reflect_iteration = 0
            MAX_REFLECT_ITERATIONS = settings.max_reflect_iterations

            while reflect_iteration < MAX_REFLECT_ITERATIONS:
                yield make_event(SSEEventType.agent_thought, "reflect_and_expand",
                    f"Reviewing coverage (iteration {reflect_iteration + 1}/{MAX_REFLECT_ITERATIONS})...")
                yield make_event(SSEEventType.tool_call, "reflect_and_expand", {
                    "bugs_found": len(all_bugs),
                    "flows_tested": len(tested_flows),
                    "iteration": reflect_iteration + 1
                })
                extra_cases = await reflect_and_expand(all_bugs, tested_flows, sitemap)
                yield make_event(SSEEventType.tool_result, "reflect_and_expand", {
                    "new_cases_found": len(extra_cases),
                    "cases": [{"id": tc.id, "title": tc.title} for tc in extra_cases]
                })

                if not extra_cases:
                    yield make_event(SSEEventType.agent_thought, "reflect_and_expand",
                        "Coverage is sufficient. No additional test cases needed.")
                    break

                yield make_event(SSEEventType.agent_thought, "reflect_and_expand",
                    f"Found {len(extra_cases)} coverage gap(s). Running follow-up tests...")

                for tc in extra_cases:
                    yield make_event(SSEEventType.tool_call, "execute_test", {
                        "test_id": tc.id, "title": tc.title, "type": tc.type, "progress": "reflect"
                    })
                    result = await execute_test(tc, url, settings.screenshot_dir)
                    all_results.append(result)
                    tested_flows.append(tc.title)
                    if not result.passed:
                        failed_pairs.append((tc, result))
                        yield make_event(SSEEventType.tool_call, "classify_bug", {
                            "test_id": result.test_id,
                            "title": tc.title,
                            "error_preview": (result.error_message or "")[:120]
                        })
                        bug = await classify_bug(tc, result)

                        # Skip false positives — never add to report
                        if bug.severity.value == "false_positive" or \
                           "false positive" in bug.root_cause_hypothesis.lower():
                            logger.info("Skipping false positive (reflect): %s", bug.title)
                            yield make_event(SSEEventType.agent_thought, "classify_bug",
                                f"Skipping false positive: '{bug.title[:50]}' — element appears to be working as designed.")
                            yield make_event(SSEEventType.tool_result, "execute_test", {
                                "test_id": result.test_id, "passed": result.passed,
                                "error_message": result.error_message, "screenshot_path": result.screenshot_path
                            })
                            continue

                        # Generate fix suggestion for Critical and Major bugs
                        if bug.severity.value in ("Critical", "Major"):
                            yield make_event(SSEEventType.agent_thought, "suggest_fix",
                                f"Generating fix suggestion for {bug.severity.value} bug: {bug.title[:50]}...")
                            
                            yield make_event(SSEEventType.tool_call, "suggest_fix", {
                                "test_id": bug.test_id,
                                "severity": bug.severity.value,
                                "title": bug.title
                            })

                            fix = await suggest_fix(bug, tc)
                            bug.fix_suggestion = fix

                            yield make_event(SSEEventType.tool_result, "suggest_fix", {
                                "test_id": bug.test_id,
                                "fix_suggestion": fix[:150] + "..." if len(fix) > 150 else fix
                            })

                        all_bugs.append(bug)
                        yield make_event(SSEEventType.tool_result, "execute_test", {
                            "test_id": result.test_id, "passed": result.passed,
                            "error_message": result.error_message, "screenshot_path": result.screenshot_path
                        })
                        yield make_event(SSEEventType.tool_result, "classify_bug", {
                            "test_id": bug.test_id, "severity": bug.severity.value, "title": bug.title,
                            "has_fix_suggestion": bug.fix_suggestion is not None
                        })
                    else:
                        yield make_event(SSEEventType.tool_result, "execute_test", {
                            "test_id": result.test_id, "passed": True, "duration_ms": result.duration_ms
                        })

                reflect_iteration += 1

            # ── STEP 6: GENERATE REPORT ────────────────────────────────────
            run_duration_ms = int((time.time() - pipeline_start) * 1000)

            yield make_event(SSEEventType.agent_thought, "generate_report",
                f"Compiling final report. Total run time: {run_duration_ms}ms.")
            yield make_event(SSEEventType.tool_call, "generate_report", {
                "total_tests": len(all_results),
                "total_bugs": len(all_bugs),
                "run_duration_ms": run_duration_ms
            })
            report = await generate_report(all_results, all_bugs, url, run_duration_ms)
            yield make_event(SSEEventType.tool_result, "generate_report", {
                "summary": report.summary,
                "total_tests": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "recommendations": report.recommendations
            })

            yield make_event(SSEEventType.agent_thought, "generate_report",
                "SentinelQA run complete. Report ready.")

            # ── FINAL COMPLETE EVENT ───────────────────────────────────────
            yield make_event(SSEEventType.complete, "done", {
                "report": report.model_dump()
            })
            _last_run_cache["report"] = report.model_dump()
            _last_run_cache["url"] = url
            _last_run_cache["timestamp"] = datetime.utcnow().isoformat()
        except Exception as e:
            yield make_event(SSEEventType.error, "pipeline", {"message": str(e)})

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@router.get("/last-run")
async def get_last_run():
    """Returns cached result of the most recent completed agent run."""
    if not _last_run_cache:
        return {"status": "no_run_yet", "data": None}
    return {"status": "ok", "data": _last_run_cache}
