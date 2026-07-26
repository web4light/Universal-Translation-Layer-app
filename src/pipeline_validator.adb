--  ============================================================================
--  Pipeline_Validator - Ada/SPARK text & prompt length / JSON validator
--
--  --el: Validates STT text, Gemini translation prompts, and Gemini
--        translation responses flowing through the Karel IV. pipeline.
--        Reads a JSON file (--json <path>) containing a "text" field and
--        validates it against the bounds appropriate for the requested
--        pipeline stage (--stage <stt|translate|response>).
--
--  Bounds (reused from Pipeline_Types, not redefined here):
--    stt / translate : Is_Valid_Text_Length     -> 1 .. MAX_PROMPT_LENGTH   (8192)
--    response        : Is_Valid_Response_Length -> 1 .. MAX_RESPONSE_LENGTH (32768)
--    all stages       : Validate_No_Null_Bytes   -> rejects embedded NUL bytes
--
--  CLI:
--    pipeline_validator --stage <stt|translate|response> --json <path>
--
--  Exit codes:
--    0 = valid    (stdout: {"valid": true, "stage": "...", "timestamp": N})
--    1 = invalid  (stdout: {"valid": false, "reason": "...",
--                           "byte_offset": N, "stage": "...", "timestamp": N})
--    2 = usage error (missing/invalid --stage, missing --json, unreadable file)
--
--  Standard 700: 12g st--bra = 1 mince
--  Requirements: 3.2, 3.3, 3.4, 3.5, 13.1
--  Autor: Pan Jeskyn-
--  Asistent: Kiro
--  ============================================================================

with Ada.Text_IO;
with Ada.Command_Line;
with Ada.Strings.Fixed;
with Ada.Streams.Stream_IO;
with Ada.Calendar;
with Pipeline_Types;

procedure Pipeline_Validator with
   SPARK_Mode => On
is
   use Ada.Text_IO;

   --  Maximum bytes read from the --json input file (covers the largest
   --  legal response payload of MAX_RESPONSE_LENGTH plus JSON overhead).
   MAX_FILE_BYTES : constant Positive := 40_000;

   --  =========================================================================
   --  PURE SPARK VALIDATION FUNCTIONS  (no I/O - formally verified contracts)
   --  =========================================================================

   --  True when Text length is within the STT/prompt bound (1 .. 8192).
   --  Reuses Pipeline_Types.Is_Valid_Text_Length rather than redefining it.
   function Validate_Text_Length (Text : String) return Boolean
      with
         Post => Validate_Text_Length'Result =
                 (Text'Length >= 1 and
                  Text'Length <= Pipeline_Types.MAX_PROMPT_LENGTH)
   is
   begin
      return Pipeline_Types.Is_Valid_Text_Length (Text'Length);
   end Validate_Text_Length;

   --  True when Response length is within the Gemini response bound
   --  (1 .. 32768). Reuses Pipeline_Types.Is_Valid_Response_Length.
   function Validate_Response_Length (Response : String) return Boolean
      with
         Post => Validate_Response_Length'Result =
                 (Response'Length >= 1 and
                  Response'Length <= Pipeline_Types.MAX_RESPONSE_LENGTH)
   is
   begin
      return Pipeline_Types.Is_Valid_Response_Length (Response'Length);
   end Validate_Response_Length;

   --  True when Text contains no embedded NUL bytes anywhere in its range.
   function Validate_No_Null_Bytes (Text : String) return Boolean
      with
         Post => (if Validate_No_Null_Bytes'Result then
                    (for all I in Text'Range =>
                       Text (I) /= Character'Val (0)))
   is
   begin
      for I in Text'Range loop
         if Text (I) = Character'Val (0) then
            return False;
         end if;
      end loop;
      return True;
   end Validate_No_Null_Bytes;

   --  Returns the 1-indexed offset of the first NUL byte in Text, or 0 when
   --  no NUL byte is present. Used to populate "byte_offset" on rejection.
   function First_Null_Byte_Offset (Text : String) return Natural
      with
         Post => First_Null_Byte_Offset'Result <= Text'Length
   is
   begin
      for I in Text'Range loop
         if Text (I) = Character'Val (0) then
            return I - Text'First + 1;
         end if;
      end loop;
      return 0;
   end First_Null_Byte_Offset;

   --  =========================================================================
   --  FILE / JSON I/O  (SPARK_Mode Off - OS interaction, string search)
   --  =========================================================================

   --  Read up to MAX_FILE_BYTES raw bytes from Path into Content (1..Last).
   --  OK is False when the file cannot be opened or read.
   procedure Read_File_Content
      (Path    : in  String;
       Content : out String;
       Last    : out Natural;
       OK      : out Boolean)
      with
         SPARK_Mode => Off,
         Pre  => Content'Length = MAX_FILE_BYTES
   is
      use Ada.Streams.Stream_IO;
      File      : Ada.Streams.Stream_IO.File_Type;
      Buffer    : Ada.Streams.Stream_Element_Array
                     (1 .. Ada.Streams.Stream_Element_Offset (MAX_FILE_BYTES));
      Read_Last : Ada.Streams.Stream_Element_Offset;
   begin
      OK   := False;
      Last := 0;

      begin
         Open (File, In_File, Path);
      exception
         when others => return;
      end;

      begin
         Read (File, Buffer, Read_Last);
      exception
         when others =>
            Close (File);
            return;
      end;

      Close (File);

      Last := Natural (Read_Last);
      for I in 1 .. Last loop
         Content (Content'First + I - 1) :=
            Character'Val (Natural (Buffer (Ada.Streams.Stream_Element_Offset (I))));
      end loop;
      OK := True;
   end Read_File_Content;

   --  Extract the JSON string value for key "text" from a flat JSON object.
   --  Returns the value between the first pair of quotes following the key,
   --  or an empty string when the key is missing / not a string field.
   function Extract_Text_Field (Json : String) return String
      with SPARK_Mode => Off
   is
      use Ada.Strings.Fixed;
      Search_Key : constant String := """text""";
      Key_Pos    : Natural;
      Val_Start  : Natural;
      Val_End    : Natural;
   begin
      if Json'Length = 0 then
         return "";
      end if;

      Key_Pos := Index (Json, Search_Key);
      if Key_Pos = 0 then
         return "";
      end if;

      Val_Start := Key_Pos + Search_Key'Length;
      while Val_Start <= Json'Last and then
            (Json (Val_Start) = ' ' or Json (Val_Start) = ':') loop
         Val_Start := Val_Start + 1;
      end loop;

      if Val_Start > Json'Last or else Json (Val_Start) /= '"' then
         return "";
      end if;
      Val_Start := Val_Start + 1;  --  skip opening quote

      Val_End := Val_Start;
      while Val_End <= Json'Last and then Json (Val_End) /= '"' loop
         Val_End := Val_End + 1;
      end loop;

      if Val_End > Json'Last or else Val_End - 1 < Val_Start then
         return "";
      end if;

      return Json (Val_Start .. Val_End - 1);
   end Extract_Text_Field;

   --  =========================================================================
   --  TIMESTAMP  (SPARK_Mode Off - Ada.Calendar)
   --  =========================================================================

   function Get_Unix_Timestamp return Natural
      with SPARK_Mode => Off
   is
      use Ada.Calendar;
      Epoch : constant Time     := Time_Of (1970, 1, 1, 0.0);
      Diff  : constant Duration := Clock - Epoch;
   begin
      if Diff <= 0.0 then
         return 0;
      end if;
      return Natural (Diff);
   end Get_Unix_Timestamp;

   --  =========================================================================
   --  CLI ARGUMENT HELPERS  (SPARK_Mode Off - Ada.Command_Line)
   --  =========================================================================

   function Get_Flag_Arg (Flag : String) return String
      with SPARK_Mode => Off
   is
      use Ada.Command_Line;
   begin
      for I in 1 .. Argument_Count - 1 loop
         if Argument (I) = Flag then
            return Argument (I + 1);
         end if;
      end loop;
      return "";
   end Get_Flag_Arg;

   procedure Set_Exit (Code : Natural)
      with SPARK_Mode => Off
   is
   begin
      Ada.Command_Line.Set_Exit_Status
         (Ada.Command_Line.Exit_Status (Code));
   end Set_Exit;

   --  =========================================================================
   --  JSON OUTPUT BUILDERS  (SPARK_Mode Off - Natural'Image, concatenation)
   --  =========================================================================

   function Build_Valid_Json
      (Stage : String; Timestamp : Natural) return String
      with SPARK_Mode => Off
   is
   begin
      return "{""valid"": true, ""stage"": """ & Stage &
             """, ""timestamp"": " & Natural'Image (Timestamp) & "}";
   end Build_Valid_Json;

   function Build_Invalid_Json
      (Stage       : String;
       Reason      : String;
       Byte_Offset : Natural;
       Timestamp   : Natural) return String
      with SPARK_Mode => Off
   is
   begin
      return "{""valid"": false, ""reason"": """ & Reason &
             """, ""byte_offset"": " & Natural'Image (Byte_Offset) &
             ", ""stage"": """ & Stage &
             """, ""timestamp"": " & Natural'Image (Timestamp) & "}";
   end Build_Invalid_Json;

   --  =========================================================================
   --  MAIN LOGIC
   --  =========================================================================

   Stage_Arg : constant String := Get_Flag_Arg ("--stage");
   Json_Arg  : constant String := Get_Flag_Arg ("--json");

begin
   --  -------------------------------------------------------------------------
   --  Usage checks (exit 2)
   --  -------------------------------------------------------------------------
   if Stage_Arg /= "stt" and Stage_Arg /= "translate" and
      Stage_Arg /= "response"
   then
      Put_Line ("ERROR: --stage must be one of: stt | translate | response");
      Set_Exit (2);
      return;
   end if;

   if Json_Arg = "" then
      Put_Line ("ERROR: missing --json <path> argument");
      Set_Exit (2);
      return;
   end if;

   declare
      File_Buffer : String (1 .. MAX_FILE_BYTES);
      File_Last   : Natural;
      File_OK     : Boolean;
   begin
      Read_File_Content
         (Path    => Json_Arg,
          Content => File_Buffer,
          Last    => File_Last,
          OK      => File_OK);

      if not File_OK then
         Put_Line ("ERROR: cannot read JSON file " & Json_Arg);
         Set_Exit (2);
         return;
      end if;

      declare
         Json_Content : constant String := File_Buffer (1 .. File_Last);
         Text_Field   : constant String := Extract_Text_Field (Json_Content);
         Timestamp    : constant Natural := Get_Unix_Timestamp;

         Length_OK    : Boolean;
      begin
         if Stage_Arg = "response" then
            Length_OK := Validate_Response_Length (Text_Field);
         else
            Length_OK := Validate_Text_Length (Text_Field);
         end if;

         --  ----------------------------------------------------------------
         --  Length bound failure
         --  ----------------------------------------------------------------
         if not Length_OK then
            Put_Line
               (Build_Invalid_Json
                  (Stage       => Stage_Arg,
                   Reason      => "text length" &
                                   " out of bounds for stage " & Stage_Arg,
                   Byte_Offset => Text_Field'Length,
                   Timestamp   => Timestamp));
            Set_Exit (1);
            return;
         end if;

         --  ----------------------------------------------------------------
         --  Null byte failure
         --  ----------------------------------------------------------------
         if not Validate_No_Null_Bytes (Text_Field) then
            Put_Line
               (Build_Invalid_Json
                  (Stage       => Stage_Arg,
                   Reason      => "text contains embedded null byte",
                   Byte_Offset => First_Null_Byte_Offset (Text_Field),
                   Timestamp   => Timestamp));
            Set_Exit (1);
            return;
         end if;

         --  ----------------------------------------------------------------
         --  All checks passed
         --  ----------------------------------------------------------------
         Put_Line (Build_Valid_Json (Stage => Stage_Arg, Timestamp => Timestamp));
         Set_Exit (0);
      end;
   end;

end Pipeline_Validator;
