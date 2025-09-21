import React, { useState, useEffect } from "react";
import { AlertCircle } from "lucide-react";

interface FormData {
  firstName: string;
  lastName: string;
  dob: string;
  sex: string;
  address: string;
  nationality: string;
  passportNumber: string;
  licenseNumber: string;
}

interface RegistrationFormProps {
  initialData: Partial<FormData>;
}

const emptyForm: FormData = {
  firstName: "",
  lastName: "",
  dob: "",
  sex: "",
  address: "",
  nationality: "",
  passportNumber: "",
  licenseNumber: "",
};

const RegistrationForm: React.FC<RegistrationFormProps> = ({ initialData }) => {
  const [form, setForm] = useState<FormData>(emptyForm);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, boolean>>>({});

  useEffect(() => {
    if (!initialData || Object.keys(initialData).length === 0) {
      // reset form kosong jika scan ulang
      setForm(emptyForm);
      setErrors({});
      return;
    }

    // merge hasil OCR ke form
    setForm((prev) => ({ ...prev, ...initialData }));

    const newErrors: Partial<Record<keyof FormData, boolean>> = {};
    Object.keys(initialData).forEach((key) => {
      const formKey = key as keyof FormData;
      const value = initialData[formKey];
      if (!value || String(value).trim() === "") {
        newErrors[formKey] = true;
      }
    });
    setErrors(newErrors);
  }, [initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
    if (value.trim() !== "") {
      setErrors((prev) => ({ ...prev, [name]: false }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`Data Tersimpan:\n${JSON.stringify(form, null, 2)}`);
  };

  const inputClass = (fieldName: keyof FormData) =>
    `w-full px-3 py-2 bg-gray-50 border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${errors[fieldName] ? "border-red-400 ring-red-200" : "border-gray-300"}`;

  const errorText = (fieldName: keyof FormData) =>
    errors[fieldName] && (
      <p className="flex items-center gap-1 text-xs text-red-600 mt-1">
        <AlertCircle size={14} /> Data ini perlu diisi atau diperbaiki.
      </p>
    );

  return (
    <div className="bg-white p-6 rounded-2xl shadow-lg w-full max-w-lg animate-fade-in" style={{ animationDelay: "150ms" }}>
      <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-3">
        <div className="bg-indigo-600 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold">2</div>
        Extracted Information
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* First + Last Name */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">First Name</label>
            <input name="firstName" value={form.firstName} onChange={handleChange} placeholder="e.g., John" className={inputClass("firstName")} />
            {errorText("firstName")}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Last Name</label>
            <input name="lastName" value={form.lastName} onChange={handleChange} placeholder="e.g., Doe" className={inputClass("lastName")} />
            {errorText("lastName")}
          </div>
        </div>

        {/* Address */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Address</label>
          <input name="address" value={form.address} onChange={handleChange} placeholder="Enter full address" className={inputClass("address")} />
          {errorText("address")}
        </div>

        {/* DOB + Sex */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Date of Birth</label>
            <input name="dob" type="date" value={form.dob} onChange={handleChange} className={inputClass("dob")} />
            {errorText("dob")}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Sex</label>
            <input name="sex" value={form.sex} onChange={handleChange} placeholder="M / F" className={inputClass("sex")} />
            {errorText("sex")}
          </div>
        </div>

        {/* Nationality */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Nationality</label>
          <input name="nationality" value={form.nationality} onChange={handleChange} placeholder="e.g., Indonesian" className={inputClass("nationality")} />
          {errorText("nationality")}
        </div>

        {/* Passport + License */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Passport Number</label>
            <input name="passportNumber" value={form.passportNumber} onChange={handleChange} placeholder="Passport No." className={inputClass("passportNumber")} />
            {errorText("passportNumber")}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">License Number</label>
            <input name="licenseNumber" value={form.licenseNumber} onChange={handleChange} placeholder="License No." className={inputClass("licenseNumber")} />
            {errorText("licenseNumber")}
          </div>
        </div>

        <div className="pt-2">
          <button type="submit" className="w-full bg-green-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:bg-green-400 transform hover:scale-105">
            Save Registration
          </button>
        </div>
      </form>
    </div>
  );
};

export default RegistrationForm;
