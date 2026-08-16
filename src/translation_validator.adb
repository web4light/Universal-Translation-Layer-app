--  ============================================================================
--  Translation_Validator - UTL Translation Integrity Validator
--
--  Purpose: Validates translation output/input length ratios for each
--           language pair. Uses expansion factor lookup table to determine
--           acceptable bounds. Reads JSON from stdin, outputs JSON to stdout.
--
--  Standard: Ada/SPARK 2022
--  Verification: gnatprove --level=4
--
--  Standard 700: 12g stribra = 1 mince
--  Autor: Pan Jeskyne
--  Asistent: Kiro (Claude Sonnet 4)
--  ============================================================================

with Ada.Text_IO;       use Ada.Text_IO;
with Pipeline_Types;    use Pipeline_Types;

procedure Translation_Validator is

   --  =========================================================================
   --  CONSTANTS
   --  =========================================================================

   MAX_EXPANSION : constant Natural := 10;
   --  Maximum expansion factor for any language pair (characters).

   --  =========================================================================
   --  EXPANSION FACTOR LOOKUP TABLE
   --  =========================================================================

   --  Returns the maximum expansion factor for a source->target language pair.
   --  Realistic factors based on linguistic properties:
   --    EN->DE ~1.3, EN->JA ~0.5 (chars), CS->EN ~1.2, EN->FR ~1.2, etc.
   --  We return integer ceiling multipliers for SPARK provability.
   function Max_Expansion_Factor
     (Source : Language_Code;
      Target : Language_Code) return Natural
   with
      Post => Max_Expansion_Factor'Result >= 1
              and Max_Expansion_Factor'Result <= MAX_EXPANSION
   is
   begin
      --  Same language: identity (ratio 1)
      if Source = Target then
         return 1;
      end if;

      --  Language-specific expansion factors
      case Source is
         when CS =>
            case Target is
               when EN => return 2;   --  Czech -> English: ~1.2x
               when DE => return 2;   --  Czech -> German: ~1.3x
               when FR => return 2;   --  Czech -> French: ~1.3x
               when JA => return 3;   --  Czech -> Japanese: variable
               when ES => return 2;   --  Czech -> Spanish: ~1.2x
               when IT => return 2;   --  Czech -> Italian: ~1.2x
               when PL => return 2;   --  Czech -> Polish: ~1.1x
               when SK => return 2;   --  Czech -> Slovak: ~1.0x
               when CS => return 1;   --  unreachable
            end case;

         when EN =>
            case Target is
               when CS => return 2;   --  English -> Czech: ~1.1x
               when DE => return 2;   --  English -> German: ~1.3x
               when FR => return 2;   --  English -> French: ~1.2x
               when JA => return 3;   --  English -> Japanese: ~0.5x chars
               when ES => return 2;   --  English -> Spanish: ~1.3x
               when IT => return 2;   --  English -> Italian: ~1.2x
               when PL => return 2;   --  English -> Polish: ~1.2x
               when SK => return 2;   --  English -> Slovak: ~1.1x
               when EN => return 1;   --  unreachable
            end case;

         when DE =>
            case Target is
               when CS => return 2;   --  German -> Czech: ~0.9x
               when EN => return 2;   --  German -> English: ~0.9x
               when FR => return 2;   --  German -> French: ~1.1x
               when JA => return 3;   --  German -> Japanese: variable
               when ES => return 2;   --  German -> Spanish: ~1.1x
               when IT => return 2;   --  German -> Italian: ~1.1x
               when PL => return 2;   --  German -> Polish: ~1.0x
               when SK => return 2;   --  German -> Slovak: ~0.9x
               when DE => return 1;   --  unreachable
            end case;

         when FR =>
            case Target is
               when CS => return 2;   --  French -> Czech: ~0.9x
               when EN => return 2;   --  French -> English: ~0.9x
               when DE => return 2;   --  French -> German: ~1.1x
               when JA => return 3;   --  French -> Japanese: variable
               when ES => return 2;   --  French -> Spanish: ~1.0x
               when IT => return 2;   --  French -> Italian: ~1.0x
               when PL => return 2;   --  French -> Polish: ~1.0x
               when SK => return 2;   --  French -> Slovak: ~0.9x
               when FR => return 1;   --  unreachable
            end case;

         when JA =>
            case Target is
               when CS => return 4;   --  Japanese -> Czech: ~2.5x chars
               when EN => return 4;   --  Japanese -> English: ~2.5x chars
               when DE => return 5;   --  Japanese -> German: ~3.0x chars
               when FR => return 4;   --  Japanese -> French: ~2.5x chars
               when ES => return 4;   --  Japanese -> Spanish: ~2.5x chars
               when IT => return 4;   --  Japanese -> Italian: ~2.5x chars
               when PL => return 4;   --  Japanese -> Polish: ~2.5x chars
               when SK => return 4;   --  Japanese -> Slovak: ~2.5x chars
               when JA => return 1;   --  unreachable
            end case;

         when ES =>
            case Target is
               when CS => return 2;   --  Spanish -> Czech: ~0.9x
               when EN => return 2;   --  Spanish -> English: ~0.9x
               when DE => return 2;   --  Spanish -> German: ~1.1x
               when FR => return 2;   --  Spanish -> French: ~1.0x
               when JA => return 3;   --  Spanish -> Japanese: variable
               when IT => return 2;   --  Spanish -> Italian: ~1.0x
               when PL => return 2;   --  Spanish -> Polish: ~1.0x
               when SK => return 2;   --  Spanish -> Slovak: ~0.9x
               when ES => return 1;   --  unreachable
            end case;

         when IT =>
            case Target is
               when CS => return 2;   --  Italian -> Czech: ~0.9x
               when EN => return 2;   --  Italian -> English: ~0.9x
               when DE => return 2;   --  Italian -> German: ~1.1x
               when FR => return 2;   --  Italian -> French: ~1.0x
               when JA => return 3;   --  Italian -> Japanese: variable
               when ES => return 2;   --  Italian -> Spanish: ~1.0x
               when PL => return 2;   --  Italian -> Polish: ~1.0x
               when SK => return 2;   --  Italian -> Slovak: ~0.9x
               when IT => return 1;   --  unreachable
            end case;

         when PL =>
            case Target is
               when CS => return 2;   --  Polish -> Czech: ~1.0x
               when EN => return 2;   --  Polish -> English: ~1.0x
               when DE => return 2;   --  Polish -> German: ~1.2x
               when FR => return 2;   --  Polish -> French: ~1.1x
               when JA => return 3;   --  Polish -> Japanese: variable
               when ES => return 2;   --  Polish -> Spanish: ~1.1x
               when IT => return 2;   --  Polish -> Italian: ~1.1x
               when SK => return 2;   --  Polish -> Slovak: ~1.0x
               when PL => return 1;   --  unreachable
            end case;

         when SK =>
            case Target is
               when CS => return 2;   --  Slovak -> Czech: ~1.0x
               when EN => return 2;   --  Slovak -> English: ~1.1x
               when DE => return 2;   --  Slovak -> German: ~1.3x
               when FR => return 2;   --  Slovak -> French: ~1.2x
               when JA => return 3;   --  Slovak -> Japanese: variable
               when ES => return 2;   --  Slovak -> Spanish: ~1.2x
               when IT => return 2;   --  Slovak -> Italian: ~1.1x
               when PL => return 2;   --  Slovak -> Polish: ~1.0x
               when SK => return 1;   --  unreachable
            end case;
      end case;
   end Max_Expansion_Factor;

   --  =========================================================================
   --  VALIDATION FUNCTION
   --  =========================================================================

   --  Validates that the translation output length is within acceptable bounds
   --  for the given language pair.
   function Validate_Translation_Ratio
     (Input_Length  : Natural;
      Output_Length : Natural;
      Source_Lang   : Language_Code;
      Target_Lang   : Language_Code) return Boolean
   with
      Pre  => Input_Length > 0
              and Input_Length <= MAX_PROMPT_LENGTH,
      Post => Validate_Translation_Ratio'Result =
              (Output_Length > 0
               and then Output_Length <=
                   Input_Length * Max_Expansion_Factor (Source_Lang, Target_Lang))
   is
      Factor : constant Natural :=
        Max_Expansion_Factor (Source_Lang, Target_Lang);
   begin
      return Output_Length > 0
             and then Output_Length <= Input_Length * Factor;
   end Validate_Translation_Ratio;

   --  =========================================================================
   --  JSON PARSING HELPERS (minimal, SPARK-compatible)
   --  =========================================================================

   --  Maximum input line length for JSON parsing.
   MAX_LINE_LENGTH : constant := 4096;

   subtype Line_Buffer is String (1 .. MAX_LINE_LENGTH);

   --  Parse a natural number from a string starting at Pos.
   --  Returns 0 if no valid number found.
   function Parse_Natural
     (Buf : Line_Buffer;
      Pos : Natural;
      Len : Natural) return Natural
   with
      Pre  => Pos >= 1 and Pos <= MAX_LINE_LENGTH
              and Len >= 1 and Len <= MAX_LINE_LENGTH,
      Post => Parse_Natural'Result >= 0
   is
      Result : Natural := 0;
      I      : Natural := Pos;
   begin
      while I <= Len and then I <= MAX_LINE_LENGTH loop
         exit when Buf (I) < '0' or Buf (I) > '9';
         --  Guard against overflow
         if Result > (Natural'Last - 9) / 10 then
            return Result;
         end if;
         Result := Result * 10 +
                   (Character'Pos (Buf (I)) - Character'Pos ('0'));
         I := I + 1;
      end loop;
      return Result;
   end Parse_Natural;

   --  Find position of a substring in the buffer.
   --  Returns 0 if not found.
   function Find_Substr
     (Buf     : Line_Buffer;
      Buf_Len : Natural;
      Key     : String) return Natural
   with
      Pre  => Buf_Len >= 0 and Buf_Len <= MAX_LINE_LENGTH
              and Key'Length >= 1 and Key'Length <= 64,
      Post => Find_Substr'Result <= MAX_LINE_LENGTH
   is
      Key_Len : constant Natural := Key'Length;
   begin
      if Key_Len > Buf_Len then
         return 0;
      end if;
      for I in 1 .. Buf_Len - Key_Len + 1 loop
         if Buf (I .. I + Key_Len - 1) = Key then
            return I;
         end if;
      end loop;
      return 0;
   end Find_Substr;

   --  Find the numeric value after a given key in JSON.
   --  Looks for pattern: "key": <number>
   function Get_Json_Natural
     (Buf     : Line_Buffer;
      Buf_Len : Natural;
      Key     : String) return Natural
   with
      Pre  => Buf_Len >= 0 and Buf_Len <= MAX_LINE_LENGTH
              and Key'Length >= 1 and Key'Length <= 60,
      Post => Get_Json_Natural'Result >= 0
   is
      Pos : Natural;
      I   : Natural;
   begin
      Pos := Find_Substr (Buf, Buf_Len, Key);
      if Pos = 0 then
         return 0;
      end if;
      --  Skip past key and find colon then digits
      I := Pos + Key'Length;
      while I <= Buf_Len and then I <= MAX_LINE_LENGTH loop
         exit when Buf (I) >= '0' and Buf (I) <= '9';
         I := I + 1;
      end loop;
      if I > Buf_Len or I > MAX_LINE_LENGTH then
         return 0;
      end if;
      return Parse_Natural (Buf, I, Buf_Len);
   end Get_Json_Natural;

   --  Extract a short string value after a given key.
   --  Returns the two-letter language code or empty.
   function Get_Json_Lang
     (Buf     : Line_Buffer;
      Buf_Len : Natural;
      Key     : String) return Language_Code
   with
      Pre  => Buf_Len >= 0 and Buf_Len <= MAX_LINE_LENGTH
              and Key'Length >= 1 and Key'Length <= 60
   is
      Pos : Natural;
      I   : Natural;
      C1  : Character;
      C2  : Character;
   begin
      Pos := Find_Substr (Buf, Buf_Len, Key);
      if Pos = 0 then
         return CS;  --  default
      end if;
      --  Skip past key, find opening quote of value
      I := Pos + Key'Length;
      while I <= Buf_Len and then I <= MAX_LINE_LENGTH loop
         exit when Buf (I) = '"';
         I := I + 1;
      end loop;
      --  Skip the opening quote
      I := I + 1;
      if I + 1 > Buf_Len or I + 1 > MAX_LINE_LENGTH then
         return CS;
      end if;
      --  Read two characters (language code)
      C1 := Buf (I);
      C2 := Buf (I + 1);

      --  Match uppercase language codes
      if (C1 = 'C' or C1 = 'c') and (C2 = 'S' or C2 = 's') then
         return CS;
      elsif (C1 = 'E' or C1 = 'e') and (C2 = 'N' or C2 = 'n') then
         return EN;
      elsif (C1 = 'D' or C1 = 'd') and (C2 = 'E' or C2 = 'e') then
         return DE;
      elsif (C1 = 'F' or C1 = 'f') and (C2 = 'R' or C2 = 'r') then
         return FR;
      elsif (C1 = 'J' or C1 = 'j') and (C2 = 'A' or C2 = 'a') then
         return JA;
      elsif (C1 = 'E' or C1 = 'e') and (C2 = 'S' or C2 = 's') then
         return ES;
      elsif (C1 = 'I' or C1 = 'i') and (C2 = 'T' or C2 = 't') then
         return IT;
      elsif (C1 = 'P' or C1 = 'p') and (C2 = 'L' or C2 = 'l') then
         return PL;
      elsif (C1 = 'S' or C1 = 's') and (C2 = 'K' or C2 = 'k') then
         return SK;
      else
         return CS;  --  default fallback
      end if;
   end Get_Json_Lang;

   --  =========================================================================
   --  MAIN LOGIC
   --  =========================================================================

   Buf         : Line_Buffer := (others => ' ');
   Buf_Len     : Natural := 0;
   Input_Len   : Natural;
   Output_Len  : Natural;
   Source_Lang  : Language_Code;
   Target_Lang  : Language_Code;
   Valid       : Boolean;
   Stage_Name  : constant String := "Text_Translate";

begin
   --  Read one line of JSON from stdin
   if End_Of_File then
      Put_Line ("{""valid"": false, ""reason"": ""empty input"", " &
                """stage"": """ & Stage_Name & """}");
      return;
   end if;

   declare
      Raw_Line : constant String := Get_Line;
      Copy_Len : Natural;
   begin
      Copy_Len := Natural'Min (Raw_Line'Length, MAX_LINE_LENGTH);
      Buf (1 .. Copy_Len) := Raw_Line (Raw_Line'First .. Raw_Line'First + Copy_Len - 1);
      Buf_Len := Copy_Len;
   end;

   --  Parse JSON fields
   Input_Len   := Get_Json_Natural (Buf, Buf_Len, """input_length""");
   Output_Len  := Get_Json_Natural (Buf, Buf_Len, """output_length""");
   Source_Lang := Get_Json_Lang (Buf, Buf_Len, """source_lang""");
   Target_Lang := Get_Json_Lang (Buf, Buf_Len, """target_lang""");

   --  Validate preconditions
   if Input_Len = 0 then
      Put_Line ("{""valid"": false, ""reason"": ""input_length must be > 0"", " &
                """stage"": """ & Stage_Name & """}");
      return;
   end if;

   if Input_Len > MAX_PROMPT_LENGTH then
      Put_Line ("{""valid"": false, " &
                """reason"": ""input_length exceeds maximum"", " &
                """stage"": """ & Stage_Name & """}");
      return;
   end if;

   --  Run validation
   Valid := Validate_Translation_Ratio (Input_Len, Output_Len,
                                        Source_Lang, Target_Lang);

   --  Output result as JSON
   if Valid then
      Put_Line ("{""valid"": true, ""reason"": ""ratio within bounds"", " &
                """stage"": """ & Stage_Name & """}");
   else
      Put_Line ("{""valid"": false, " &
                """reason"": ""output length outside expansion bounds"", " &
                """stage"": """ & Stage_Name & """}");
   end if;

end Translation_Validator;
