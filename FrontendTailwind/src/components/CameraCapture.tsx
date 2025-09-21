import React, { useState, useRef, Suspense } from "react";
import { type Crop, type PixelCrop } from "react-image-crop";
import { Camera, Upload, CheckCircle, RefreshCw, Loader, AlertCircle } from "lucide-react";

// Lazy load ReactCrop
const ReactCrop = React.lazy(() => import("react-image-crop"));

interface ExtractedData {
  firstName: string;
  lastName: string;
  address: string;
  dob: string;
  sex: string;
  nationality: string;
  passportNumber: string;
  licenseNumber: string;
}

interface CameraCaptureProps {
  onExtractedData: (data: Partial<ExtractedData>) => void;
}

const CameraCapture: React.FC<CameraCaptureProps> = ({ onExtractedData }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const [isCameraOn, setIsCameraOn] = useState(false);
  const [captured, setCaptured] = useState(false);
  const [dataUrl, setDataUrl] = useState("");
  const [crop, setCrop] = useState<Crop>({
    unit: "%",
    x: 2,
    y: 2,
    width: 96,
    height: 96,
  });
  const [completedCrop, setCompletedCrop] = useState<PixelCrop | null>(null);
  const [showCrop, setShowCrop] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // -------------------------
  // Camera handling
  // -------------------------
  const startCamera = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraOn(true);
      }
    } catch (err) {
      console.error("Error accessing camera:", err);
      setError("Kamera tidak dapat diakses. Pastikan Anda memberikan izin.");
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
    }
    setIsCameraOn(false);
  };

  const capturePhoto = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) {
      setError("Video stream belum siap.");
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
    const capturedDataUrl = canvas.toDataURL("image/png");
    setDataUrl(capturedDataUrl);
    setShowCrop(true);
    stopCamera();
  };

  // -------------------------
  // Upload file
  // -------------------------
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError("");
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.addEventListener("load", () => setDataUrl(reader.result?.toString() || ""));
      reader.readAsDataURL(file);
      setShowCrop(true);
      stopCamera();
    }
  };

  // -------------------------
  // Crop and convert to File
  // -------------------------
  const getCroppedImage = async (image: HTMLImageElement, cropData: PixelCrop): Promise<File> => {
    const canvas = document.createElement("canvas");
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    const pixelX = cropData.x * scaleX;
    const pixelY = cropData.y * scaleY;
    const pixelWidth = cropData.width * scaleX;
    const pixelHeight = cropData.height * scaleY;

    canvas.width = pixelWidth;
    canvas.height = pixelHeight;

    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Could not get canvas context");

    ctx.drawImage(image, pixelX, pixelY, pixelWidth, pixelHeight, 0, 0, pixelWidth, pixelHeight);

    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("Gagal membuat blob dari canvas."));
            return;
          }
          const file = new File([blob], "cropped.jpg", { type: "image/jpeg" });
          resolve(file);
        },
        "image/jpeg",
        1
      );
    });
  };

  // -------------------------
  // Upload cropped image
  // -------------------------
  const uploadCropped = async () => {
    if (!dataUrl || !imgRef.current || !completedCrop) return;
    setLoading(true);
    setError("");

    try {
      const croppedFile = await getCroppedImage(imgRef.current, completedCrop);

      const formData = new FormData();
      formData.append("file", croppedFile);

      const res = await fetch("http://127.0.0.1:8000/detect", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`Server merespon dengan status: ${res.status}`);

      const data = await res.json();

      if (data.success && data.parsed) {
        const { parsed } = data;
        const normalizeDate = (value: string) => {
          if (!value) return "";
          const m = value.match(/^(\d{2})[./-](\d{2})[./-](\d{4})$/);
          if (m) {
            return parseInt(m[1], 10) > 12 ? `${m[3]}-${m[2]}-${m[1]}` : `${m[3]}-${m[1]}-${m[2]}`;
          }
          const m2 = value.match(/^(\d{4})[./-](\d{2})[./-](\d{2})$/);
          if (m2) return value.replace(/[./-]/g, "-");
          return value;
        };

        onExtractedData({
          firstName: parsed.firstName || parsed.givenNames || "",
          lastName: parsed.lastName || parsed.surname || "",
          address: parsed.address || "",
          dob: normalizeDate(parsed.dateOfBirth) || "",
          sex: parsed.sex || parsed.gender || "",
          nationality: parsed.StateName || parsed.nationality || "",
          passportNumber: parsed.passportNumber || "",
          licenseNumber: parsed.licenseNumber || "",
        });

        setCaptured(true);
        setShowCrop(false);
      } else {
        throw new Error(data.message || "Ekstraksi OCR gagal. Coba lagi.");
      }
    } catch (err: unknown) {
      console.error(err);
      let errorMessage = "Terjadi kesalahan. Periksa koneksi atau coba gambar lain.";
      if (err instanceof Error) errorMessage = err.message;
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // -------------------------
  // Reset untuk scan ulang
  // -------------------------
  const handleRetake = () => {
    onExtractedData({
      firstName: "",
      lastName: "",
      address: "",
      dob: "",
      sex: "",
      nationality: "",
      passportNumber: "",
      licenseNumber: "",
    });

    setCaptured(false);
    setDataUrl("");
    setShowCrop(false);
    setIsCameraOn(false);
    setError("");
  };

  // -------------------------
  // UI Components
  // -------------------------
  const fallbackSpinner = (
    <div className="absolute inset-0 bg-black bg-opacity-70 flex flex-col items-center justify-center gap-3 text-white">
      <Loader size={40} className="animate-spin" />
      <p className="font-semibold text-lg">Memuat...</p>
    </div>
  );

  return (
    <div className="bg-white p-6 rounded-2xl shadow-lg w-full max-w-lg flex flex-col gap-4 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-3">
        <div className="bg-indigo-600 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold">1</div>
        Scan Document
      </h2>

      {/* Camera / Crop Container */}
      <div className="relative w-full min-h-[300px] bg-gray-900 rounded-lg overflow-hidden flex items-center justify-center group">
        {!showCrop ? (
          <>
            {captured && dataUrl ? (
              <img src={dataUrl} alt="Captured" className="max-w-full max-h-[80vh] object-contain" />
            ) : (
              <>
                <video ref={videoRef} autoPlay playsInline className={`w-full h-full object-contain transition-opacity duration-300 ${isCameraOn ? "opacity-100" : "opacity-0"}`}></video>

                {/* Box panduan untuk ID Card */}
                {isCameraOn && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="border-4 border-white rounded-lg w-[85%] aspect-[1.585/1]"></div>
                  </div>
                )}

                {!isCameraOn && !captured && (
                  <div className="absolute inset-0 bg-black bg-opacity-60 flex flex-col items-center justify-center gap-4 p-4 text-center">
                    <Camera size={48} className="text-white opacity-70" />
                    <p className="text-white font-medium">Nyalakan kamera atau unggah gambar</p>
                  </div>
                )}
              </>
            )}
          </>
        ) : (
          <Suspense fallback={fallbackSpinner}>
            <ReactCrop crop={crop} onChange={(c) => setCrop(c)} onComplete={(c) => setCompletedCrop(c)} aspect={undefined}>
              <img ref={imgRef} src={dataUrl} alt="Crop Target" className="max-w-full max-h-[80vh] object-contain" />
            </ReactCrop>
          </Suspense>
        )}

        {loading && (
          <div className="absolute inset-0 bg-black bg-opacity-70 flex flex-col items-center justify-center gap-3 text-white">
            <Loader size={40} className="animate-spin" />
            <p className="font-semibold text-lg">Mengekstrak data...</p>
          </div>
        )}
      </div>

      <canvas ref={canvasRef} className="hidden" />

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-3 rounded-md flex items-start gap-2">
          <AlertCircle size={20} className="flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        {!isCameraOn && !captured && !showCrop && (
          <>
            <button onClick={startCamera} className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 text-white font-semibold px-4 py-3 rounded-lg hover:bg-indigo-700 transition-all transform hover:scale-105">
              <Camera size={18} /> Start Camera
            </button>
            <label className="flex-1 cursor-pointer flex items-center justify-center gap-2 bg-gray-100 text-gray-700 font-semibold px-4 py-3 rounded-lg hover:bg-gray-200 transition-all text-center transform hover:scale-105">
              <Upload size={18} /> Upload File
              <input type="file" accept="image/jpeg, image/png" onChange={handleFileChange} className="hidden" />
            </label>
          </>
        )}

        {isCameraOn && !showCrop && (
          <button onClick={capturePhoto} className="w-full bg-red-500 text-white font-semibold px-4 py-3 rounded-lg hover:bg-red-600 transition-colors shadow-lg">
            Ambil Gambar
          </button>
        )}

        {showCrop && (
          <button onClick={uploadCropped} disabled={loading} className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white font-semibold px-4 py-3 rounded-lg hover:bg-indigo-700 disabled:bg-indigo-400 transition-colors">
            {loading ? (
              <>
                <Loader size={18} className="animate-spin" /> Processing...
              </>
            ) : (
              "Ekstrak Data dari Gambar"
            )}
          </button>
        )}

        {captured && !showCrop && (
          <div className="w-full flex flex-col sm:flex-row items-center gap-4 bg-green-50 border border-green-200 p-4 rounded-lg">
            <CheckCircle className="text-green-600" size={32} />
            <span className="flex-1 text-green-800 font-semibold text-center sm:text-left">Data berhasil diekstrak!</span>
            <button onClick={handleRetake} className="flex items-center gap-2 bg-gray-600 text-white font-semibold px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors">
              <RefreshCw size={16} /> Scan Ulang
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraCapture;
