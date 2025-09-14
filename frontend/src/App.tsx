import React, { useState } from "react";
import CameraCapture from "./components/CameraCapture";
import RegistrationForm from "./components/RegistrationForm";
import "./styles/ocr.css";

export default function App() {
  const [extractedData, setExtractedData] = useState<Record<string, string>>({});
  console.log("Current extractedData:", extractedData);
  return (
    <div className="app-container">
      <h1 className="title">Registration with Camera + OCR</h1>

      <div className="scanner-section">
        <CameraCapture onExtractedData={setExtractedData} />
        <RegistrationForm initialData={extractedData} />
      </div>
    </div>
  );
}
