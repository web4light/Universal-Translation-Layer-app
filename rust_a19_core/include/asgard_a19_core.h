#ifndef ASGARD_A19_CORE_H
#define ASGARD_A19_CORE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float x;
    float y;
    float z;
} AsgardVec3;

typedef struct {
    AsgardVec3 mid;
    AsgardVec3 tip;
} AsgardFingerJoints;

typedef struct {
    AsgardVec3 shoulder;
    AsgardVec3 elbow;
    AsgardVec3 wrist;
    AsgardFingerJoints fingers[5];
} AsgardArmPose;

typedef struct __attribute__((aligned(64))) {
    float timestamp_sec;
    uint32_t active_gloss_id;
    float breath_offset_y;
    float head_tilt_rad;
    float mouth_open;
    float energy_pulse;
    AsgardArmPose left_arm;
    AsgardArmPose right_arm;
} AsgardAvatarPoseFrame;

/** Inicializuje on-device A19 Pro AI engine v RAM (vrací 1 při úspěchu). */
int32_t asgard_a19_init(void);

/** Spustí on-device překlad a analýzu znakových glos (vrací JSON C-string). */
char* asgard_a19_infer_json(const char* input_utf8, const char* target_lang_utf8);

/** Vypočítá 120 FPS kinematický snímek 3D znakového avatara přímo do out_frame. */
int32_t asgard_a19_solve_avatar_frame(float timestamp_sec, uint32_t gloss_id, AsgardAvatarPoseFrame* out_frame);

/** Spustí protokol 04:23 Ash Sweeper (Zero-Trace RAM skartace). */
uint64_t asgard_a19_ash_sweep_423(void);

/** Uvolní řetězec vrácený funkcí asgard_a19_infer_json. */
void asgard_a19_free_string(char* ptr);

#ifdef __cplusplus
}
#endif

#endif /* ASGARD_A19_CORE_H */
