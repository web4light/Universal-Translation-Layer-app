//! 3D Holografický Znakový Avatar — 120 FPS ProMotion Kinematický Engine v Rustu.
//!
//! Počítá artikulovanou kostru humanoidního avatara (ramena, lokty, zápěstí,
//! 5 prstů se 2 články na každé ruce, dýchání hrudníku, sklon hlavy a artikulaci rtů)
//! přímo v unifikované paměti čipu A19 Pro bez jediné halové alokace.

use crate::a19_tensor::SignGloss;

/// 3D bod / vektor v prostoru avatara.
#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct Vec3 {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

/// Artikulace jednoho prstu (základní kloub a koncový článek).
#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct FingerJoints {
    /// Střední kloub prstu (PIP).
    pub mid: Vec3,
    /// Špička prstu (Tip).
    pub tip: Vec3,
}

/// Kompletní stav jedné paže a ruky vč. 5 prstů.
#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct ArmPose {
    /// Pozice ramenního kloubu.
    pub shoulder: Vec3,
    /// Pozice loketního kloubu.
    pub elbow: Vec3,
    /// Pozice zápěstí / dlaně.
    pub wrist: Vec3,
    /// 5 prstů (palec, ukazováček, prostředníček, prsteníček, malíček).
    pub fingers: [FingerJoints; 5],
}

/// Kompletní snímek (frame) pózy 3D avatara zarovnaný pro Metal GPU / C-FFI.
#[repr(C, align(64))]
#[derive(Debug, Clone, Copy, Default)]
pub struct AvatarPoseFrame {
    /// Časové razítko snímku v sekundách.
    pub timestamp_sec: f32,
    /// Aktuálně vykreslovaná znaková glosa (0..6).
    pub active_gloss_id: u32,
    /// Posun hrudníku vlivem organického dýchání.
    pub breath_offset_y: f32,
    /// Náklon hlavy (non-manuální gramatika znakového jazyka).
    pub head_tilt_rad: f32,
    /// Otevření rtů (0.0 = zavřeno, 1.0 = plná artikulace).
    pub mouth_open: f32,
    /// Intenzita kyber-aury kolem dlaní (0.0 .. 1.0).
    pub energy_pulse: f32,
    /// Levá paže a ruka.
    pub left_arm: ArmPose,
    /// Pravá paže a ruka.
    pub right_arm: ArmPose,
}

/// Vypočítá kompletní kinematický snímek 3D avatara pro daný čas `t` (v sekundách) a znakovou glosu.
#[inline]
pub fn solve_avatar_pose(t: f32, gloss: SignGloss) -> AvatarPoseFrame {
    let breath_offset_y = (t * 2.0).sin() * 2.0;
    let head_tilt_rad = (t * 1.5).sin() * 0.05;

    let l_shoulder = Vec3 {
        x: -36.0,
        y: -15.0 + breath_offset_y,
        z: 0.0,
    };
    let r_shoulder = Vec3 {
        x: 36.0,
        y: -15.0 + breath_offset_y,
        z: 0.0,
    };

    let (l_elbow, l_wrist, r_elbow, r_wrist, energy_pulse, finger_spread) = match gloss {
        SignGloss::Idle => {
            let idle_wave = (t * 1.5).sin() * 3.0;
            (
                Vec3 { x: -48.0, y: 28.0 + breath_offset_y, z: 4.0 },
                Vec3 { x: -38.0, y: 55.0 + idle_wave, z: 8.0 },
                Vec3 { x: 48.0, y: 28.0 + breath_offset_y, z: 4.0 },
                Vec3 { x: 38.0, y: 55.0 - idle_wave, z: 8.0 },
                0.0,
                0.35,
            )
        }
        SignGloss::Welcome => {
            let w = (t * 3.0).sin();
            (
                Vec3 { x: -55.0 - w * 8.0, y: 10.0, z: 12.0 },
                Vec3 { x: -65.0 - w * 18.0, y: -20.0 - w * 12.0, z: 24.0 },
                Vec3 { x: 55.0 + w * 8.0, y: 10.0, z: 12.0 },
                Vec3 { x: 65.0 + w * 18.0, y: -20.0 - w * 12.0, z: 24.0 },
                (w.abs() * 0.85).clamp(0.2, 1.0),
                0.9,
            )
        }
        SignGloss::Accessibility => {
            let angle = t * 4.0;
            let cx = angle.cos() * 16.0;
            let sy = angle.sin() * 16.0;
            (
                Vec3 { x: -45.0, y: 15.0, z: 15.0 },
                Vec3 { x: -22.0 + cx, y: 5.0 + sy, z: 28.0 },
                Vec3 { x: 45.0, y: 15.0, z: 15.0 },
                Vec3 { x: 22.0 - cx, y: 5.0 - sy, z: 28.0 },
                0.92,
                0.75,
            )
        }
        SignGloss::Thanks => {
            let phase = (t * 2.5).sin().abs();
            (
                Vec3 { x: -46.0, y: 26.0, z: 6.0 },
                Vec3 { x: -34.0, y: 48.0, z: 10.0 },
                Vec3 { x: 42.0, y: 8.0, z: 18.0 },
                Vec3 { x: 10.0 + phase * 18.0, y: -18.0 + phase * 24.0, z: 15.0 + phase * 20.0 },
                0.78,
                0.85,
            )
        }
        SignGloss::Sovereign => {
            // Zkřížený štít před hrudníkem (SPARK Guardian postoj)
            let pulse = (t * 3.5).sin().abs();
            (
                Vec3 { x: -42.0, y: 12.0, z: 18.0 },
                Vec3 { x: 8.0, y: -6.0, z: 30.0 },
                Vec3 { x: 42.0, y: 12.0, z: 18.0 },
                Vec3 { x: -8.0, y: -6.0, z: 32.0 },
                0.95 * pulse.max(0.5),
                0.5,
            )
        }
        SignGloss::Solar => {
            // Zvednuté dlaně ke Slunci (Solární Genesis)
            let rise = (t * 2.0).sin() * 6.0;
            (
                Vec3 { x: -52.0, y: -18.0, z: 14.0 },
                Vec3 { x: -38.0, y: -52.0 + rise, z: 22.0 },
                Vec3 { x: 52.0, y: -18.0, z: 14.0 },
                Vec3 { x: 38.0, y: -52.0 + rise, z: 22.0 },
                1.0,
                1.0,
            )
        }
        SignGloss::Babylon => {
            // Spirálový vzestup rukou (Věž Babylon / Univerzální spojení)
            let spiral = t * 3.2;
            (
                Vec3 { x: -46.0, y: 5.0, z: 16.0 },
                Vec3 { x: -24.0 + spiral.cos() * 14.0, y: -15.0 - (t.sin().abs() * 25.0), z: 26.0 },
                Vec3 { x: 46.0, y: 5.0, z: 16.0 },
                Vec3 { x: 24.0 - spiral.cos() * 14.0, y: -15.0 - (t.cos().abs() * 25.0), z: 26.0 },
                0.98,
                0.88,
            )
        }
    };

    let left_arm = build_arm_with_fingers(l_shoulder, l_elbow, l_wrist, t, finger_spread, -1.0);
    let right_arm = build_arm_with_fingers(r_shoulder, r_elbow, r_wrist, t, finger_spread, 1.0);

    let mouth_open = if energy_pulse > 0.25 {
        ((t * 8.0).sin().abs() * energy_pulse).clamp(0.1, 0.95)
    } else {
        0.0
    };

    AvatarPoseFrame {
        timestamp_sec: t,
        active_gloss_id: gloss as u32,
        breath_offset_y,
        head_tilt_rad,
        mouth_open,
        energy_pulse,
        left_arm,
        right_arm,
    }
}

/// Vypočítá 5 dvoučlánkových prstů pro dané zápěstí.
#[inline]
fn build_arm_with_fingers(
    shoulder: Vec3,
    elbow: Vec3,
    wrist: Vec3,
    t: f32,
    spread: f32,
    side_sign: f32,
) -> ArmPose {
    let base_angle = (wrist.y - elbow.y).atan2(wrist.x - elbow.x);
    let mut fingers = [FingerJoints::default(); 5];

    for idx in 0..5 {
        let f_offset = (idx as f32) - 2.0; // -2, -1, 0, 1, 2
        let micro_curl = ((t * 5.0 + f_offset).sin()) * 0.12 * spread;
        let f_angle = base_angle + f_offset * (0.22 * spread) + micro_curl * side_sign;

        let mid = Vec3 {
            x: wrist.x + f_angle.cos() * 9.0,
            y: wrist.y + f_angle.sin() * 9.0,
            z: wrist.z + 2.0,
        };
        let tip = Vec3 {
            x: mid.x + (f_angle + micro_curl).cos() * 7.5,
            y: mid.y + (f_angle + micro_curl).sin() * 7.5,
            z: mid.z + 1.5,
        };
        fingers[idx] = FingerJoints { mid, tip };
    }

    ArmPose {
        shoulder,
        elbow,
        wrist,
        fingers,
    }
}
