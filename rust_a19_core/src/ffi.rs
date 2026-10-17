//! C-FFI Rozhraní pro iOS (Swift / Xcode / Flutter `dart:ffi`) na čipu Apple A19 Pro.
//!
//! Poskytuje bezalokační a bezpečné funkce s C ABI (`extern "C"`), které umožňují
//! přímé volání z mobilní aplikace na iPhonu přes unifikovanou paměť (UMA).

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::sync::Mutex;

use crate::a19_tensor::{A19NeuralEngine, SignGloss};
use crate::avatar_kinematics::{solve_avatar_pose, AvatarPoseFrame};

/// Globální instance A19 Pro enginu v RAM chráněná synchronizačním zámkem.
static ENGINE: Mutex<Option<A19NeuralEngine>> = Mutex::new(None);

/// Inicializuje on-device A19 Pro AI engine v RAM.
/// Vrací `1` při úspěchu, `0` při chybě.
#[no_mangle]
pub extern "C" fn asgard_a19_init() -> i32 {
    if let Ok(mut guard) = ENGINE.lock() {
        *guard = Some(A19NeuralEngine::new());
        1
    } else {
        0
    }
}

/// Spustí on-device překlad a sémantickou analýzu pro 3D avatara na čipu A19 Pro.
///
/// Vrácený C řetězec je nutné uvolnit zavoláním `asgard_a19_free_string`.
#[no_mangle]
pub unsafe extern "C" fn asgard_a19_infer_json(
    input_utf8: *const c_char,
    target_lang_utf8: *const c_char,
) -> *mut c_char {
    if input_utf8.is_null() || target_lang_utf8.is_null() {
        return std::ptr::null_mut();
    }

    let text = match CStr::from_ptr(input_utf8).to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };
    let lang = match CStr::from_ptr(target_lang_utf8).to_str() {
        Ok(s) => s,
        Err(_) => "CS",
    };

    let mut guard = match ENGINE.lock() {
        Ok(g) => g,
        Err(_) => return std::ptr::null_mut(),
    };

    if guard.is_none() {
        *guard = Some(A19NeuralEngine::new());
    }

    let engine = guard.as_mut().unwrap();
    let res = engine.infer(text, lang);

    // Sestavíme kompaktní JSON odpověď bez externích závislostí
    let escaped_translation = res
        .translated_text
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', " ");

    let gloss_ids: Vec<String> = res
        .gloss_sequence
        .iter()
        .map(|g| (*g as u32).to_string())
        .collect();

    let json = format!(
        "{{\"status\":\"ok\",\"chip\":\"Apple A19 Pro (UMA Zero-Copy)\",\"translated\":\"{}\",\"primary_gloss_id\":{},\"primary_gloss_label\":\"{}\",\"gloss_sequence\":[{}],\"confidence\":{:.4},\"latency_us\":{},\"ram_arena_used_bytes\":{}}}",
        escaped_translation,
        res.primary_gloss as u32,
        res.primary_gloss.label_cs(),
        gloss_ids.join(","),
        res.confidence,
        res.latency_us,
        engine.arena.used_bytes()
    );

    match CString::new(json) {
        Ok(cstr) => cstr.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Vypočítá jeden 120 FPS kinematický snímek 3D znakového avatara přímo do předané struktury.
/// Nulová alokace na haldě (Zero-Copy přímo do bufferu volajícího).
#[no_mangle]
pub unsafe extern "C" fn asgard_a19_solve_avatar_frame(
    timestamp_sec: f32,
    gloss_id: u32,
    out_frame: *mut AvatarPoseFrame,
) -> i32 {
    if out_frame.is_null() {
        return 0;
    }
    let gloss = match gloss_id {
        1 => SignGloss::Welcome,
        2 => SignGloss::Accessibility,
        3 => SignGloss::Thanks,
        4 => SignGloss::Sovereign,
        5 => SignGloss::Solar,
        6 => SignGloss::Babylon,
        _ => SignGloss::Idle,
    };

    let frame = solve_avatar_pose(timestamp_sec, gloss);
    std::ptr::write(out_frame, frame);
    1
}

/// Spustí protokol 04:23 Ash Sweeper — okamžité kryptografické vymazání Zero-Trace RAM arény.
/// Vrací celkový počet provedených skartací v této relaci.
#[no_mangle]
pub extern "C" fn asgard_a19_ash_sweep_423() -> u64 {
    if let Ok(mut guard) = ENGINE.lock() {
        if let Some(ref mut engine) = *guard {
            engine.arena.ash_sweep_423();
            return engine.arena.sweeps_count;
        }
    }
    0
}

/// Uvolní řetězec alokovaný funkcí `asgard_a19_infer_json`.
#[no_mangle]
pub unsafe extern "C" fn asgard_a19_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        let _ = CString::from_raw(ptr);
    }
}
