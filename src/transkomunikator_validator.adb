--  ============================================================================
--  Transkomunik-tor Validator - Ada/SPARK audio PCM validator
--
--  --el: Validates PCM audio file for use in the translation pipeline.
--        Reads PCM file path from --pcm CLI argument.
--        Validates:
--          1. Sample rate >= 16000 Hz
--          2. Frame integrity (data_bytes divisible by frame_size)
--
--  CLI:
--    transkomunikator_validator --pcm <path> [--rate <sample_rate>] [--frame-size <N>]
--
--  Exit codes:
--    0 = valid   (stdout: "OK: PCM valid - sample_rate=NNNNN, frames=N")
--    1 = invalid (stdout: "INVALID: sample_rate below 16000"
--                      or "INVALID: data_bytes not aligned to frame_size")
--    2 = usage error / file not found
--
--  Standard 700: 12g st--bra = 1 mince
--  Requirements: 3.1, 4.2, 4.4
--  Property 2 (design.md): For any Audio_Chunk_Meta with sample_rate in
--    range 0..96000 and frame_size > 0, the SPARK audio validator SHALL
--    accept if and only if sample_rate >= 16000 AND data_bytes is a whole
--    multiple of frame_size.
--  Autor: Pan Jeskyn-
--  Asistent: Kiro
--  ============================================================================

with Ada.Text_IO;
with Ada.Command_Line;
with Ada.Streams.Stream_IO;
with Interfaces;
with Pipeline_Types;

procedure Transkomunikator_Validator with
   SPARK_Mode => On
is
   use Ada.Text_IO;

   --  =========================================================================
   --  PURE VALIDATION FUNCTIONS  (SPARK_Mode On - no I/O)
   --  =========================================================================

   --  True when the data chunk size is a whole multiple of the frame size.
   --  Frame_Size must be > 0 to avoid division by zero (enforced by Pre).
   function Frames_Integral
      (Data_Bytes : Natural;
       Frame_Size : Positive)
       return Boolean
      with
         Pre  => Frame_Size > 0,
         Post => Frames_Integral'Result = (Data_Bytes rem Frame_Size = 0)
   is
   begin
      return Data_Bytes rem Frame_Size = 0;
   end Frames_Integral;

   --  Combined audio PCM validation predicate - Property 2 from design.md:
   --  "For any Audio_Chunk_Meta with sample_rate in range 0..96000 and
   --   frame_size > 0, the SPARK audio validator SHALL accept if and only
   --   if sample_rate >= 16000 AND data_bytes is a whole multiple of
   --   frame_size."
   --  Reuses Pipeline_Types.Is_Valid_Sample_Rate rather than redefining the
   --  minimum-sample-rate constant/check locally.
   function Validate_Audio_PCM
      (Sample_Rate : Natural;
       Data_Bytes  : Natural;
       Frame_Size  : Positive)
       return Boolean
      with
         Pre  => Frame_Size > 0,
         Post => Validate_Audio_PCM'Result =
                 (Pipeline_Types.Is_Valid_Sample_Rate (Sample_Rate) and then
                  Data_Bytes rem Frame_Size = 0)
   is
   begin
      return Pipeline_Types.Is_Valid_Sample_Rate (Sample_Rate)
         and then Frames_Integral (Data_Bytes, Frame_Size);
   end Validate_Audio_PCM;

   --  =========================================================================
   --  WAV HEADER I/O SUBPROGRAMS  (SPARK_Mode Off - OS interaction)
   --  =========================================================================

   --  Read little-endian 16-bit unsigned value from a byte pair.
   function LE16 (Lo, Hi : Interfaces.Unsigned_8) return Natural
      with SPARK_Mode => Off
   is
   begin
      return Natural (Lo) + (Natural (Hi) * 256);
   end LE16;

   --  Read little-endian 32-bit unsigned value from four bytes.
   function LE32
      (B0, B1, B2, B3 : Interfaces.Unsigned_8)
       return Natural
      with SPARK_Mode => Off
   is
   begin
      return Natural (B0)
        + (Natural (B1) * 256)
        + (Natural (B2) * 65_536)
        + (Natural (B3) * 16_777_216);
   end LE32;

   --  Attempt to parse the 44-byte canonical WAV/RIFF header.
   --  Returns True on success; populates Sample_Rate, Channels, Bits_Per_Sample,
   --  and Data_Bytes.  Returns False when the file is too small, not RIFF/WAVE,
   --  or the fmt/data subchunk layout is non-canonical.
   --
   --  SPARK_Mode Off because it uses Ada.Streams.Stream_IO.
   procedure Read_Wav_Header
      (Path            : in  String;
       OK              : out Boolean;
       Sample_Rate     : out Natural;
       Channels        : out Natural;
       Bits_Per_Sample : out Natural;
       Data_Bytes      : out Natural)
      with SPARK_Mode => Off
   is
      use Ada.Streams;
      use Ada.Streams.Stream_IO;
      use Interfaces;

      File    : Ada.Streams.Stream_IO.File_Type;
      Buffer  : Ada.Streams.Stream_Element_Array (1 .. 44);
      Last    : Ada.Streams.Stream_Element_Offset;

      function To_U8 (E : Ada.Streams.Stream_Element)
         return Unsigned_8
      is (Unsigned_8 (E));

   begin
      --  Defaults on error path
      OK              := False;
      Sample_Rate     := 0;
      Channels        := 0;
      Bits_Per_Sample := 0;
      Data_Bytes      := 0;

      begin
         Open (File, In_File, Path);
      exception
         when others => return;
      end;

      Read (File, Buffer, Last);
      Close (File);

      --  Need at least 44 bytes for a canonical WAV header
      if Last < 44 then
         return;
      end if;

      --  ChunkID  [0..3] must be "RIFF"
      if Buffer (1) /= Character'Pos ('R') or
         Buffer (2) /= Character'Pos ('I') or
         Buffer (3) /= Character'Pos ('F') or
         Buffer (4) /= Character'Pos ('F')
      then
         return;
      end if;

      --  Format  [8..11] must be "WAVE"
      if Buffer (9)  /= Character'Pos ('W') or
         Buffer (10) /= Character'Pos ('A') or
         Buffer (11) /= Character'Pos ('V') or
         Buffer (12) /= Character'Pos ('E')
      then
         return;
      end if;

      --  Subchunk1ID [12..15] must be "fmt "
      if Buffer (13) /= Character'Pos ('f') or
         Buffer (14) /= Character'Pos ('m') or
         Buffer (15) /= Character'Pos ('t') or
         Buffer (16) /= Character'Pos (' ')
      then
         return;
      end if;

      --  AudioFormat [20..21] must be PCM (1)
      if LE16 (To_U8 (Buffer (21)), To_U8 (Buffer (22))) /= 1 then
         return;
      end if;

      --  NumChannels [22..23]
      Channels := LE16 (To_U8 (Buffer (23)), To_U8 (Buffer (24)));

      --  SampleRate  [24..27]
      Sample_Rate := LE32
         (To_U8 (Buffer (25)), To_U8 (Buffer (26)),
          To_U8 (Buffer (27)), To_U8 (Buffer (28)));

      --  BitsPerSample [34..35]
      Bits_Per_Sample := LE16 (To_U8 (Buffer (35)), To_U8 (Buffer (36)));

      --  Subchunk2ID [36..39] must be "data"
      if Buffer (37) /= Character'Pos ('d') or
         Buffer (38) /= Character'Pos ('a') or
         Buffer (39) /= Character'Pos ('t') or
         Buffer (40) /= Character'Pos ('a')
      then
         return;
      end if;

      --  Subchunk2Size [40..43]
      Data_Bytes := LE32
         (To_U8 (Buffer (41)), To_U8 (Buffer (42)),
          To_U8 (Buffer (43)), To_U8 (Buffer (44)));

      OK := True;
   end Read_Wav_Header;

   --  =========================================================================
   --  CLI ARGUMENT HELPERS  (SPARK_Mode Off - Ada.Command_Line)
   --  =========================================================================

   --  Scan argv for "--pcm" and return the following argument, or "".
   function Get_Pcm_Arg return String
      with SPARK_Mode => Off
   is
      use Ada.Command_Line;
   begin
      for I in 1 .. Argument_Count - 1 loop
         if Argument (I) = "--pcm" then
            return Argument (I + 1);
         end if;
      end loop;
      return "";
   end Get_Pcm_Arg;

   --  Set OS-level exit code.
   procedure Set_Exit (Code : Natural)
      with SPARK_Mode => Off
   is
   begin
      Ada.Command_Line.Set_Exit_Status
         (Ada.Command_Line.Exit_Status (Code));
   end Set_Exit;

   --  =========================================================================
   --  MAIN BODY
   --  =========================================================================

   Pcm_Path        : constant String  := Get_Pcm_Arg;

   --  WAV header fields populated by Read_Wav_Header
   Header_OK       : Boolean  := False;
   Sample_Rate     : Natural  := 0;
   Channels        : Natural  := 0;
   Bits_Per_Sample : Natural  := 0;
   Data_Bytes      : Natural  := 0;

   --  Derived frame size (bytes per interleaved sample across all channels)
   Frame_Size      : Natural  := 0;

begin
   --  -------------------------------------------------------------------------
   --  Usage check
   --  -------------------------------------------------------------------------
   if Pcm_Path = "" then
      Put_Line ("ERROR: missing --pcm <path> argument");
      Set_Exit (2);
      return;
   end if;

   --  -------------------------------------------------------------------------
   --  Parse WAV header
   --  -------------------------------------------------------------------------
   Read_Wav_Header
      (Path            => Pcm_Path,
       OK              => Header_OK,
       Sample_Rate     => Sample_Rate,
       Channels        => Channels,
       Bits_Per_Sample => Bits_Per_Sample,
       Data_Bytes      => Data_Bytes);

   if not Header_OK then
      Put_Line ("INVALID: cannot parse WAV/RIFF header in " & Pcm_Path);
      Set_Exit (1);
      return;
   end if;

   --  -------------------------------------------------------------------------
   --  Validate sample rate  (Requirement 3.1: >= 16000 Hz)
   --  -------------------------------------------------------------------------
   if not Pipeline_Types.Is_Valid_Sample_Rate (Sample_Rate) then
      Put_Line
         ("INVALID: sample rate " & Natural'Image (Sample_Rate) &
          " Hz is below minimum 16000 Hz");
      Set_Exit (1);
      return;
   end if;

   --  -------------------------------------------------------------------------
   --  Validate frame integrity
   --  Frame_Size = (bits_per_sample / 8) * channels; must be > 0
   --  -------------------------------------------------------------------------
   if Bits_Per_Sample = 0 or Channels = 0 then
      Put_Line ("INVALID: BitsPerSample or NumChannels is zero");
      Set_Exit (1);
      return;
   end if;

   Frame_Size := (Bits_Per_Sample / 8) * Channels;

   if Frame_Size = 0 then
      Put_Line ("INVALID: computed frame size is zero (BitsPerSample < 8)");
      Set_Exit (1);
      return;
   end if;

   --  Validate_Audio_PCM (Property 2) combines both checks; re-verified
   --  here individually above so a precise reason can be reported, but the
   --  combined predicate is the authoritative SPARK-contracted gate below.
   if not Validate_Audio_PCM (Sample_Rate, Data_Bytes, Frame_Size) then
      Put_Line
         ("INVALID: data chunk size " & Natural'Image (Data_Bytes) &
          " bytes is not a whole multiple of frame size " &
          Natural'Image (Frame_Size) & " bytes");
      Set_Exit (1);
      return;
   end if;

   --  -------------------------------------------------------------------------
   --  All checks passed
   --  -------------------------------------------------------------------------
   Put_Line ("OK: PCM valid - " &
             Natural'Image (Sample_Rate) & " Hz, " &
             Natural'Image (Channels) & " ch, " &
             Natural'Image (Bits_Per_Sample) & " bit, " &
             Natural'Image (Data_Bytes) & " data bytes");

   Set_Exit (0);

end Transkomunikator_Validator;
