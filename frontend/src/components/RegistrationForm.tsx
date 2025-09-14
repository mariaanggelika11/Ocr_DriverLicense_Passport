import React, { useState, useEffect } from "react";

interface Props {
  initialData?: Record<string, string>;
}

export default function RegistrationForm({ initialData = {} }: Props) {
  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    dob: "",
    sex: "",
    address: "",
    nationality: "",
    passportNumber: "",
    licenseNumber: "",
  });

  const [errors, setErrors] = useState<Record<string, boolean>>({});

  useEffect(() => {
    console.log("RegistrationForm received initialData:", initialData);
    if (!initialData) return;

    if (Object.keys(initialData).length === 0) {
      // Reset form + errors kalau retake
      setForm({
        firstName: "",
        lastName: "",
        dob: "",
        sex: "",
        address: "",
        nationality: "",
        passportNumber: "",
        licenseNumber: "",
      });
      setErrors({});
    } else {
      setForm((prev) => ({ ...prev, ...initialData }));

      // tandai field kosong
      const newErrors: Record<string, boolean> = {};
      Object.keys(initialData).forEach((key) => {
        if (!initialData[key] || initialData[key].trim() === "") {
          newErrors[key] = true;
        }
      });
      setErrors(newErrors);
    }
  }, [initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });

    // hilangkan tanda merah kalau user isi
    setErrors((prev) => ({
      ...prev,
      [name]: value.trim() === "" ? true : false,
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert(JSON.stringify(form, null, 2));
  };

  return (
    <div className="form-card">
      <h2>Registration Data</h2>
      <form onSubmit={handleSubmit} className="form-body">
        <div className="form-group">
          <label>First Name</label>
          <input name="firstName" value={form.firstName} onChange={handleChange} placeholder="Enter your first name" className={errors.firstName ? "input-error" : ""} />
          {errors.firstName && <div className="error-text">This field is required</div>}
        </div>

        <div className="form-group">
          <label>Last Name</label>
          <input name="lastName" value={form.lastName} onChange={handleChange} placeholder="Enter your last name" className={errors.lastName ? "input-error" : ""} />
          {errors.lastName && <div className="error-text">This field is required</div>}
        </div>

        <div className="form-group">
          <label>Address</label>
          <input name="address" value={form.address} onChange={handleChange} placeholder="Enter your address" className={errors.address ? "input-error" : ""} />
          {errors.address && <div className="error-text">This field is required</div>}
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Date of Birth</label>
            <input name="dob" type="date" value={form.dob} onChange={handleChange} className={errors.dob ? "input-error" : ""} />
            {errors.dob && <div className="error-text">This field is required</div>}
          </div>
          <div className="form-group">
            <label>Sex</label>
            <input name="sex" value={form.sex} onChange={handleChange} placeholder="M/F" className={errors.sex ? "input-error" : ""} />
            {errors.sex && <div className="error-text">This field is required</div>}
          </div>
        </div>

        <div className="form-group">
          <label>Nationality</label>
          <input name="nationality" value={form.nationality} onChange={handleChange} placeholder="Enter nationality" className={errors.nationality ? "input-error" : ""} />
          {errors.nationality && <div className="error-text">This field is required</div>}
        </div>

        <div className="form-group">
          <label>Passport Number</label>
          <input name="passportNumber" value={form.passportNumber} onChange={handleChange} placeholder="Passport No" className={errors.passportNumber ? "input-error" : ""} />
          {errors.passportNumber && <div className="error-text">This field is required</div>}
        </div>

        <div className="form-group">
          <label>License Number</label>
          <input name="licenseNumber" value={form.licenseNumber} onChange={handleChange} placeholder="License No" className={errors.licenseNumber ? "input-error" : ""} />
          {errors.licenseNumber && <div className="error-text">This field is required</div>}
        </div>

        <button type="submit" className="submit">
          Save
        </button>
      </form>
    </div>
  );
}
