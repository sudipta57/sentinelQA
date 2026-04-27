import Header from "./components/Header";
import InputPanel from "./components/InputPanel";
import ReportPanel from "./components/ReportPanel";
import StreamPanel from "./components/StreamPanel";
import { useAgentStream } from "./hooks/useAgentStream";
import { BACKEND_URL } from "./utils/api";

export default function App(): JSX.Element {
  const { events, isRunning, currentStep, report, error, startRun } = useAgentStream();

  return (
    <div className="h-screen bg-gray-50 text-gray-900 antialiased">
      <div className="flex h-full flex-col">
        <Header />

        <div className="">
          <InputPanel onRun={startRun} isRunning={isRunning} currentStep={currentStep} />
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-6 p-6 lg:flex-row">
          <div className="min-h-0 w-full lg:w-2/5">
            <StreamPanel events={events} isRunning={isRunning} />
          </div>
          <div className="min-h-0 w-full lg:w-3/5">
            <ReportPanel
              report={report}
              isRunning={isRunning}
              error={error}
              backendUrl={BACKEND_URL}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
