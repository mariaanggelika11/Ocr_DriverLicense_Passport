import React, { useRef, useState } from "react";
import ReactCrop, { Crop } from "react-image-crop";
import "react-image-crop/dist/ReactCrop.css";

interface CameraCaptureProps {
  onExtractedData: (data: Record<string, string>) => void;
}

export default function CameraCapture({ onExtractedData }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const [isCameraOn, setIsCameraOn] = useState(false);
  const [captured, setCaptured] = useState(false);
  const [dataUrl, setDataUrl] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [crop, setCrop] = useState<Crop>({ unit: "%", x: 25, y: 25, width: 50, height: 50 });

  const [completedCrop, setCompletedCrop] = useState<any>(null);
  const [showCrop, setShowCrop] = useState(false);
  const [loading, setLoading] = useState(false);

  // === Camera Start/Stop ===
  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      setIsCameraOn(true);
    }
  };

  const stopCamera = () => {
    const stream = videoRef.current?.srcObject as MediaStream;
    stream?.getTracks().forEach((track) => track.stop());
    setIsCameraOn(false);
  };

  // === Capture ===
  const capturePhoto = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    if (!video.videoWidth || !video.videoHeight) {
      return alert("Video belum siap");
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);

    const file = dataURLtoFile(canvas.toDataURL("image/png"), "capture.png");
    setFile(file);
    setDataUrl(URL.createObjectURL(file));
    setShowCrop(true);
    stopCamera();
  };

  // === Upload file manual ===
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    setFile(file);
    setDataUrl(URL.createObjectURL(file));
    setShowCrop(true);
    stopCamera();
  };

  const getCroppedImage = async (image: HTMLImageElement, crop: Crop): Promise<Blob> => {
    if (!crop || !crop.width || !crop.height) {
      throw new Error("Crop data tidak valid");
    }

    const canvas = document.createElement("canvas");
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    const cropWidth = crop.width * scaleX;
    const cropHeight = crop.height * scaleY;

    canvas.width = cropWidth;
    canvas.height = cropHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas context not found");

    ctx.drawImage(image, crop.x * scaleX, crop.y * scaleY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight);

    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) reject("Crop gagal");
          else resolve(blob);
        },
        "image/jpeg",
        1 // kualitas maksimum
      );
    });
  };

  // === Upload ===
  const uploadCropped = async () => {
    if (!file || !imgRef.current || !completedCrop) return;
    setLoading(true);
    try {
      console.log("image natural:", imgRef.current?.naturalWidth, imgRef.current?.naturalHeight);
      console.log("crop (px):", completedCrop);

      const croppedBlob = await getCroppedImage(imgRef.current, completedCrop);
      const croppedFile = new File([croppedBlob], "cropped.jpg", { type: "image/jpeg" });

      const formData = new FormData();
      formData.append("file", croppedFile);
      const res = await fetch("http://127.0.0.1:8000/detect", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("OCR response:", data);

      if (data.success) {
        const parsed = data.parsed;
        const normalizeDate = (value?: string) => {
          if (!value) return "";
          let m = value.match(/^(\d{2})[/-](\d{2})[/-](\d{4})$/);
          if (m) {
            if (parseInt(m[1], 10) > 12) {
              return `${m[3]}-${m[2]}-${m[1]}`;
            } else {
              return `${m[3]}-${m[1]}-${m[2]}`;
            }
          }
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
      } else {
        alert("OCR gagal, response tidak sukses");
      }
    } catch (err) {
      console.error(err);
      alert("OCR gagal, cek console");
    } finally {
      setLoading(false);
      setShowCrop(false);
      setCaptured(true);
    }
  };

  const dataURLtoFile = (dataurl: string, filename: string) => {
    const arr = dataurl.split(",");
    const mime = arr[0].match(/:(.*?);/)![1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) u8arr[n] = bstr.charCodeAt(n);
    return new File([u8arr], filename, { type: mime });
  };

  // === Render ===
  return (
    <div className="camera-card">
      <div style={{ position: "relative" }}>
        {/* Video Stream */}
        {!showCrop ? (
          <div style={{ position: "relative" }}>
            <video ref={videoRef} autoPlay className="video-stream"></video>

            {/* Overlay tombol start kamera */}
            {!isCameraOn && !captured && !loading && (
              <button className="start-overlay" onClick={startCamera}>
                Start Camera
              </button>
            )}
          </div>
        ) : (
          <div
            style={{
              position: "relative",
              width: "100%",
              maxHeight: 500, // bukan height fix lagi
              overflow: "hidden",
              background: "#000",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <ReactCrop crop={crop} onChange={(c) => setCrop(c)} onComplete={(c) => setCompletedCrop(c)} style={{ width: "100%", height: "100%" }}>
              <img
                ref={imgRef}
                src={dataUrl}
                alt="crop target"
                style={{
                  width: "100%",
                  maxHeight: "500px",
                  objectFit: "contain", // jaga proporsi, selalu terlihat full
                  display: "block",
                }}
              />
            </ReactCrop>
          </div>
        )}
      </div>

      <canvas ref={canvasRef} style={{ display: "none" }} />

      <div className="camera-buttons">
        {/* Pilih file manual */}
        {!isCameraOn && !captured && !showCrop && <input type="file" accept="image/jpeg, image/png" onChange={handleFileChange} />}

        {/* Capture */}
        {isCameraOn && !captured && !showCrop && (
          <button className="capture-overlay" onClick={capturePhoto}>
            Capture
          </button>
        )}

        {/* Crop & Upload */}
        {showCrop && (
          <button onClick={uploadCropped} disabled={loading}>
            {loading ? "Processing..." : "Upload & OCR"}
          </button>
        )}

        {/* Setelah OCR sukses */}
        {captured && !showCrop && !loading && (
          <button
            onClick={() => {
              setCaptured(false);
              setFile(null);
              setDataUrl("");
              onExtractedData({});
              setIsCameraOn(false);
            }}
          >
            Retake
          </button>
        )}
      </div>
    </div>
  );
}
