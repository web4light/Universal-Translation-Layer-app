//! Asgard A19 Pro & Sovereign Golem Core — On-Device AI, 3D Znakový Avatar & Ochranný Závoj v Rustu.
//!
//! Podporuje:
//! - Kvantizované Q8_0 tenzorové inference v unifikované paměti (UMA Zero-Copy)
//! - 120 FPS ProMotion 3D kinematiky znakového avatara (ramena, lokty, zápěstí, 2x5 dvoučlánkových prstů)
//! - Obousměrný Ochranný Závoj (`utlp_veil`) + Maximus Ludus Magnus Injector
//! - Zero-Trace RAM arény se skartovacím protokolem 04:23 Ash Sweeper
//! - C-FFI rozhraní pro přímé napojení

pub mod a19_tensor;
pub mod avatar_kinematics;
pub mod ffi;
pub mod utlp_veil;

pub use a19_tensor::{A19InferenceResult, A19NeuralEngine, Q8Block, SignGloss, ZeroTraceArena};
pub use avatar_kinematics::{solve_avatar_pose, ArmPose, AvatarPoseFrame, FingerJoints, Vec3};
pub use ffi::{
    asgard_a19_ash_sweep_423, asgard_a19_free_string, asgard_a19_infer_json, asgard_a19_init,
    asgard_a19_solve_avatar_frame,
};
pub use utlp_veil::{
    MaximusTrainingLesson, UtlpProtectiveVeil, VeilContainerRect, VeilPacket, VeilVerdict,
};
