# utils/state_templates.py

def yolo_to_rel_box(xc, yc, w, h):
    return (
        xc - w / 2,
        yc - h / 2,
        xc + w / 2,
        yc + h / 2
    )

STATE_TEMPLATES = {

  "Maryland": {
    # SUDAH BENAR – JANGAN DIUBAH
    "licenseNumber": yolo_to_rel_box(0.54, 0.31, 0.26, 0.075),

    # NAME → turun & sempit (hindari label)
    "name": yolo_to_rel_box(0.36, 0.46, 0.22, 0.12),

    # DOB → pindah ke baris DOB asli
    "dateOfBirth": yolo_to_rel_box(0.36, 0.70, 0.22, 0.08),

    # ADDRESS → turun + lebih lebar
    "address": yolo_to_rel_box(0.36, 0.57, 0.45, 0.13),

    # SEX → fokus ke huruf F
    "sex": yolo_to_rel_box(0.52, 0.70, 0.06, 0.07),
    },
    # Virginia sementara pakai layout serupa (nanti fine-tune)
    "Virginia": {
        "licenseNumber": yolo_to_rel_box(0.540, 0.330, 0.260, 0.080),
        "name":          yolo_to_rel_box(0.420, 0.490, 0.150, 0.110),
        "dateOfBirth":   yolo_to_rel_box(0.500, 0.400, 0.300, 0.070),
        "address":       yolo_to_rel_box(0.550, 0.600, 0.420, 0.100),
        "sex":           yolo_to_rel_box(0.690, 0.710, 0.080, 0.060),
    }
}
