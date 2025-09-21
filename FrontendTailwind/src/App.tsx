import { useState } from "react";
import CameraCapture from "./components/CameraCapture";
import RegistrationForm from "./components/RegistrationForm";

export default function App() {
  const [extractedData, setExtractedData] = useState({});

  return (
    <main className="bg-gray-50 min-h-screen w-full flex flex-col items-center p-4 sm:p-8 font-sans">
      <div className="w-full max-w-6xl mx-auto">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-extrabold text-gray-800 tracking-tight">Registration with Camera + OCR</h1>
          <p className="text-gray-500 mt-2 max-w-2xl mx-auto">Scan your ID card, passport, or driver's license to automatically fill the registration form.</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          <CameraCapture onExtractedData={setExtractedData} />
          <RegistrationForm initialData={extractedData} />
        </div>
      </div>
    </main>
  );
}
