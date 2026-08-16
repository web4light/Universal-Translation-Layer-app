--  ============================================================================
--  Pipeline_Types - Core type definitions for Karel IV. translation pipeline
--
--  Purpose: Defines shared types, enumerations, records, and constants used
--           across the entire Karel IV. real-time voice translation pipeline.
--           All types carry SPARK contracts for formal verification.
--
--  Standard: Ada/SPARK 2022
--  Verification: gnatprove --level=4
--
--  Standard 700: 12g st--bra = 1 mince
--  Autor: Pan Jeskyn-
--  Asistent: Kiro (Claude Sonnet 4)
--  ============================================================================

pragma SPARK_Mode (On);

package Pipeline_Types is

   --  =========================================================================
   --  CONSTANTS
   --  =========================================================================

   MAX_PROMPT_LENGTH   : constant Natural := 8192;   --  Max STT/Gemini prompt
   MAX_RESPONSE_LENGTH : constant Natural := 32768;  --  Max Gemini response
   MAX_FIELD_LENGTH    : constant Natural := 4096;   --  Max JSON field value
   MAX_REASON_LENGTH   : constant Natural := 256;    --  Max rejection reason

   --  =========================================================================
   --  PIPELINE STAGE ENUMERATION
   --  =========================================================================

   --  Discrete processing steps in the Karel IV. translation pipeline.
   --  Each stage has a SPARK_Validator entry and exit gate.
   type Pipeline_Stage is (
      Audio_Capture,       --  Capture from virtual sound card (16kHz/500ms)
      Audio_Validate,      --  SPARK validator: PCM frame integrity
      Speech_To_Text,      --  Whisper STT (local GPU)
      Text_Validate,       --  SPARK validator: text length/null bytes
      Translation,         --  Gemini translator via Bifrost
      Response_Validate,   --  SPARK validator: response bounds
      Text_To_Speech,      --  Edge TTS neural voice synthesis
      Audio_Output         --  Output to virtual sound card
   );

   --  =========================================================================
   --  LANGUAGE CODE ENUMERATION
   --  =========================================================================

   --  Supported language codes for the Karel IV. translation pipeline.
   --  9 languages as per requirement 2.6 and Standard 700 language repository.
   type Language_Code is (CS, EN, DE, FR, JA, ES, IT, PL, SK);

   --  =========================================================================
   --  VALIDATION RESULT RECORD
   --  =========================================================================

   --  Bounded string subtype for rejection reason messages.
   subtype Reason_String is String (1 .. MAX_REASON_LENGTH);

   --  Result of a SPARK validation gate.
   --  Every validator returns this record - no exceptions escape.
   type Validation_Result is record
      Valid     : Boolean;
      Reason   : Reason_String;
      Stage    : Pipeline_Stage;
      Timestamp : Natural;
   end record;

   --  =========================================================================
   --  AUDIO CHUNK METADATA RECORD
   --  =========================================================================

   --  Metadata describing a discrete audio chunk entering the pipeline.
   --  Range constraints enforced by SPARK Pre/Post conditions.
   type Audio_Chunk_Meta is record
      Sample_Rate     : Natural range 8000 .. 96000;
      Channels        : Natural range 1 .. 8;
      Bits_Per_Sample : Natural range 8 .. 32;
      Duration_Ms     : Natural range 0 .. 10000;
      RMS_Amplitude   : Float range 0.0 .. 1.0;
   end record;

   --  =========================================================================
   --  SYSTEM HEALTH RECORD
   --  =========================================================================

   --  Pipeline health state reported to n8n control plane and Prometheus.
   type System_Health is record
      Pipeline_Active  : Boolean;
      N8n_Reachable    : Boolean;
      Gemini_Available : Boolean;
      Whisper_Loaded   : Boolean;
      TTS_Ready        : Boolean;
      Queue_Size       : Natural range 0 .. 100;
   end record;

   --  =========================================================================
   --  HELPER FUNCTIONS WITH SPARK CONTRACTS
   --  =========================================================================

   --  Check whether a text length is within the valid prompt range.
   function Is_Valid_Text_Length (Length : Natural) return Boolean is
      (Length >= 1 and Length <= MAX_PROMPT_LENGTH)
   with
      Post => Is_Valid_Text_Length'Result =
              (Length >= 1 and Length <= MAX_PROMPT_LENGTH);

   --  Check whether a response length is within the valid response range.
   function Is_Valid_Response_Length (Length : Natural) return Boolean is
      (Length >= 1 and Length <= MAX_RESPONSE_LENGTH)
   with
      Post => Is_Valid_Response_Length'Result =
              (Length >= 1 and Length <= MAX_RESPONSE_LENGTH);

   --  Check whether a JSON field length is within the valid field range.
   function Is_Valid_Field_Length (Length : Natural) return Boolean is
      (Length >= 1 and Length <= MAX_FIELD_LENGTH)
   with
      Post => Is_Valid_Field_Length'Result =
              (Length >= 1 and Length <= MAX_FIELD_LENGTH);

   --  Check whether an audio sample rate meets the minimum pipeline requirement.
   function Is_Valid_Sample_Rate (Rate : Natural) return Boolean is
      (Rate >= 16000 and Rate <= 96000)
   with
      Post => Is_Valid_Sample_Rate'Result =
              (Rate >= 16000 and Rate <= 96000);

   --  Create a blank (padding) reason string filled with spaces.
   function Blank_Reason return Reason_String is
      (1 .. MAX_REASON_LENGTH => ' ')
   with
      Post => Blank_Reason'Result'Length = MAX_REASON_LENGTH;

   --  =========================================================================
   --  UTL-SPECIFIC PIPELINE STAGES
   --  =========================================================================

   --  Discrete processing steps in the Universal Translation Layer pipeline.
   type UTL_Stage is (
      Text_Intercept,       --  OS-level text capture
      Text_Detect_Lang,     --  Language detection
      Text_Translate,       --  Translation
      Text_Overlay,         --  Overlay rendering
      Audio_Capture_Stream, --  System audio capture
      Audio_Separate,       --  Voice separation (Demucs)
      Audio_Diarize,        --  Speaker diarization
      Audio_Transcribe,     --  STT
      Audio_Translate,      --  Translation
      Audio_Synthesize,     --  TTS
      Audio_Mix             --  Final mix
   );

   --  =========================================================================
   --  TRANSLATION VALIDATION CONSTRAINTS
   --  =========================================================================

   --  Bounds for translation output/input length ratios and latency.
   type Translation_Bounds is record
      Min_Ratio      : Float range 0.1 .. 1.0;
      Max_Ratio      : Float range 1.0 .. 10.0;
      Max_Latency_Ms : Natural range 0 .. 5000;
   end record;

   --  Per-language-pair expansion factors (validated by SPARK).
   type Language_Pair_Config is record
      Source : Language_Code;
      Target : Language_Code;
      Bounds : Translation_Bounds;
   end record;

end Pipeline_Types;
