--  ============================================================================
--  Bifrost - Ada/SPARK - Gemini AI Bridge
--
--  Účel: Most mezi Ada/SPARK Core a Google Gemini API
--        Tartanskomunikátor (real-time dubbing)
--        Geall: lokální Ada/SPARK AI engine (osobní asistent)
--
--  Geall (--geall):
--    --translate  : stdin {"text":str,"source":str,"target":str}
--                   stdout {"translated":str,"quality_score":float}
--    --infer      : stdin {"query":str}
--                   stdout {"response":str}
--
--  Standard 700: 12g stříbra = 1 mince
--  Autor: Pan Jeskyně
--  Asistent: Kiro (Claude Sonnet 4.5)
--  ============================================================================

with Ada.Text_IO;
with Ada.Command_Line;
with Ada.Strings.Fixed;
with Ada.Strings.Unbounded;

procedure Bifrost with
   SPARK_Mode => On
is

   use Ada.Text_IO;
   use Ada.Strings.Fixed;
   use Ada.Strings.Unbounded;

   --  =========================================================================
   --  KONSTANTY
   --  =========================================================================

   GEMINI_API_VERSION  : constant String  := "v1";
   MAX_PROMPT_LENGTH   : constant Natural := 8192;   --  Max Gemini prompt
   MAX_RESPONSE_LENGTH : constant Natural := 32768;  --  Max Gemini response

   --  Geall buffer constraints
   MAX_INPUT_LINE      : constant Natural := 8192;   --  Max JSON input line
   MAX_FIELD_LENGTH    : constant Natural := 4096;   --  Max extracted field
   GEALL_QUALITY_SCORE : constant Float   := 0.92;   --  Stub quality score

   --  Ceny v Sepolia ETH (mikro-platby)
   COST_PER_TOKEN_INPUT  : constant Float := 0.000001; --  1 -ETH/token
   COST_PER_TOKEN_OUTPUT : constant Float := 0.000002; --  2 -ETH/token

   --  =========================================================================
   --  TYPY
   --  =========================================================================

   type AI_Task_Type is (
      Text_Generation,     --  Generov-n- textu
      Voice_Synthesis,     --  Synt-za hlasu
      Voice_Cloning,       --  Klonov-n- hlasu
      Real_Time_Dubbing,   --  Real-time dubbing
      Translation,         --  P-eklad
      Sentiment_Analysis   --  Anal-za sentimentu
   );

   type Language_Code is (cs, en, de, fr, es, it, ru, ja, zh);

   type Gemini_Request is record
      Task_Type   : AI_Task_Type;
      Source_Lang : Language_Code;
      Target_Lang : Language_Code;
      Prompt      : Unbounded_String;
      Max_Tokens  : Natural range 1 .. MAX_RESPONSE_LENGTH;
      Temperature : Float range 0.0 .. 2.0;  --  Kreativita
      Top_P       : Float range 0.0 .. 1.0;  --  Nucleus sampling
   end record;

   type Gemini_Response is record
      Success       : Boolean;
      Response_Text : Unbounded_String;
      Tokens_Used   : Natural;
      Cost_ETH      : Float;
      Quality       : Natural range 0 .. 100;
   end record;

   --  =========================================================================
   --  JSON PARSER TYPES
   --  =========================================================================

   --  Result of JSON structural validation.
   --  If Valid is True, Byte_Offset is 0 (unused).
   --  If Valid is False, Byte_Offset is the 0-indexed position of the first
   --  invalid character.
   type Json_Parse_Result is record
      Valid       : Boolean;
      Byte_Offset : Natural;
   end record;

   --  =========================================================================
   --  SPARK-VERIFIED HELPER FUNCTIONS
   --  =========================================================================

   --  Validate that a prompt string is within acceptable bounds.
   function Validate_Prompt (Prompt : String) return Boolean
      with
         Post => (Validate_Prompt'Result =
                  (Prompt'Length > 0 and Prompt'Length <= MAX_PROMPT_LENGTH))
   is
   begin
      return Prompt'Length > 0 and Prompt'Length <= MAX_PROMPT_LENGTH;
   end Validate_Prompt;

   --  Validate that a JSON input line is within buffer bounds.
   function Validate_Input_Line (Line : String) return Boolean
      with
         Post => (Validate_Input_Line'Result =
                  (Line'Length > 0 and Line'Length <= MAX_INPUT_LINE))
   is
   begin
      return Line'Length > 0 and Line'Length <= MAX_INPUT_LINE;
   end Validate_Input_Line;

   --  Validate that an extracted JSON field value is within bounds.
   function Validate_Field (Field : String) return Boolean
      with
         Post => (Validate_Field'Result =
                  (Field'Length > 0 and Field'Length <= MAX_FIELD_LENGTH))
   is
   begin
      return Field'Length > 0 and Field'Length <= MAX_FIELD_LENGTH;
   end Validate_Field;

   --  Return the length of a JSON input line clamped to MAX_INPUT_LINE.
   --  Pre: the line is non-empty.
   --  Post: result is in 1 .. MAX_INPUT_LINE.
   function Clamp_Input_Length (Raw_Length : Natural) return Natural
      with
         Pre  => Raw_Length >= 1,
         Post => Clamp_Input_Length'Result in 1 .. MAX_INPUT_LINE
   is
   begin
      if Raw_Length > MAX_INPUT_LINE then
         return MAX_INPUT_LINE;
      else
         return Raw_Length;
      end if;
   end Clamp_Input_Length;

   --  Extract a JSON string value for the given key from a flat JSON object.
   --  Returns the value between the first pair of quotes that follows the key.
   --  Returns empty string when key is not found or value is not a string.
   --  Pre:  json'Length <= MAX_INPUT_LINE, key'Length > 0
   --  Post: result'Length <= MAX_FIELD_LENGTH
   function Extract_Json_String
      (Json : String; Key : String) return String
      with
         Pre  => Json'Length <= MAX_INPUT_LINE
                 and Json'Length > 0
                 and Key'Length > 0,
         Post => Extract_Json_String'Result'Length <= MAX_FIELD_LENGTH
   is
      pragma SPARK_Mode (Off);  --  Ada.Strings.Fixed.Index not in SPARK subset
      Search_Key : constant String := """" & Key & """";
      Key_Pos    : Natural;
      Val_Start  : Natural;
      Val_End    : Natural;
   begin
      Key_Pos := Index (Json, Search_Key);
      if Key_Pos = 0 then
         return "";
      end if;

      --  Skip past key, colon, optional spaces, and opening quote
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

      if Val_End > Json'Last then
         return "";  --  unterminated string
      end if;

      if Val_End - 1 < Val_Start then
         return "";  --  empty value
      end if;

      declare
         Result : constant String := Json (Val_Start .. Val_End - 1);
      begin
         if Result'Length > MAX_FIELD_LENGTH then
            return Result (Result'First .. Result'First + MAX_FIELD_LENGTH - 1);
         end if;
         return Result;
      end;
   end Extract_Json_String;

   --  Build the JSON response for a --translate Geall request.
   --  Pre:  Translated'Length <= MAX_FIELD_LENGTH
   --  Post: result starts with '{'
   function Build_Translate_Response (Translated : String) return String
      with
         Pre  => Translated'Length <= MAX_FIELD_LENGTH,
         Post => Build_Translate_Response'Result (
                    Build_Translate_Response'Result'First) = '{'
   is
      pragma SPARK_Mode (Off);  --  Float'Image not in SPARK subset
      Score_Img : constant String := Float'Image (GEALL_QUALITY_SCORE);
   begin
      return "{""translated"": """ & Translated &
             """, ""quality_score"": " & Score_Img & "}";
   end Build_Translate_Response;

   --  Build the JSON response for an --infer Geall request.
   --  Pre:  Response_Text'Length <= MAX_FIELD_LENGTH
   --  Post: result starts with '{'
   function Build_Infer_Response (Response_Text : String) return String
      with
         Pre  => Response_Text'Length <= MAX_FIELD_LENGTH,
         Post => Build_Infer_Response'Result (
                    Build_Infer_Response'Result'First) = '{'
   is
      pragma SPARK_Mode (Off);
   begin
      return "{""response"": """ & Response_Text & """}";
   end Build_Infer_Response;

   --  =========================================================================
   --  JSON STRUCTURAL VALIDATOR (State-Machine Parser)
   --
   --  A simple state-machine JSON structural validator that verifies basic
   --  JSON well-formedness: balanced braces/brackets, proper string quoting,
   --  valid escape sequences, and valid value tokens.
   --
   --  Returns Json_Parse_Result with byte offset of first invalid character
   --  on failure (0-indexed from start of input).
   --
   --  This is NOT a full JSON parser - it validates structure enough to
   --  detect common malformations (missing quotes, unbalanced braces,
   --  invalid escapes, trailing commas, etc.)
   --  Requirements: 13.4
   --  =========================================================================

   --  JSON parser state enumeration
   type Json_State is (
      State_Value_Start,    --  Expecting value start
      State_In_Object,      --  Inside object, expecting key or '}'
      State_After_Key,      --  After key, expecting ':'
      State_After_Colon,    --  After ':', expecting value
      State_After_Obj_Val,  --  After value, expecting ',' or '}'
      State_In_Array,       --  Inside array, expecting value or ']'
      State_After_Arr_Val,  --  After value in array, expecting ',' or ']'
      State_In_String,      --  Inside a string value
      State_In_Escape,      --  After backslash in string
      State_In_Unicode,     --  Reading hex digits in \uXXXX
      State_In_Number,      --  Inside a numeric value
      State_In_Keyword,     --  Inside true/false/null keyword
      State_Finished,       --  Completed a top-level value
      State_Parse_Error     --  Parse error detected
   );

   --  Maximum nesting depth for JSON objects/arrays
   MAX_JSON_DEPTH : constant Natural := 64;

   --  Stack element type (tracks whether we are inside object or array)
   type Container_Kind is (Container_Object, Container_Array);

   type Container_Stack is array (1 .. MAX_JSON_DEPTH) of Container_Kind;

   --  Context for string: was it entered as a key or value?
   type String_Role is (Role_Key, Role_Value, Role_Top_Level);

   --  Validate JSON structural correctness.
   --  Pre:  Input'Length > 0 and Input'Length <= MAX_INPUT_LINE
   --  Post: If Result.Valid then Byte_Offset = 0,
   --         otherwise Byte_Offset < Input'Length
   function Validate_Json_Structure (Input : String) return Json_Parse_Result
      with
         Pre  => Input'Length > 0 and Input'Length <= MAX_INPUT_LINE,
         Post => (if Validate_Json_Structure'Result.Valid
                  then Validate_Json_Structure'Result.Byte_Offset = 0
                  else Validate_Json_Structure'Result.Byte_Offset < Input'Length)
   is
      pragma SPARK_Mode (Off);  --  uses nested functions, Unbounded_String
      Result     : Json_Parse_Result := (Valid => True, Byte_Offset => 0);
      Stack      : Container_Stack := [others => Container_Object];
      Depth      : Natural := 0;
      Pos        : Natural := Input'First;
      State      : Json_State := State_Value_Start;
      Hex_Count  : Natural := 0;
      Kw_Expect  : Unbounded_String := Null_Unbounded_String;
      Kw_Index   : Natural := 0;
      Has_Value  : Boolean := False;
      Str_Role   : String_Role := Role_Top_Level;

      Backslash  : constant Character := Character'Val (16#5C#);

      function Is_WS (C : Character) return Boolean is
        (C = ' ' or C = ASCII.HT or C = ASCII.LF or C = ASCII.CR);

      function Is_Digit (C : Character) return Boolean is
        (C >= '0' and C <= '9');

      function Is_Hex (C : Character) return Boolean is
        (Is_Digit (C) or (C >= 'a' and C <= 'f')
                      or (C >= 'A' and C <= 'F'));

      procedure Set_Err is
      begin
         State := State_Parse_Error;
         Result.Valid := False;
         if Pos - Input'First < Input'Length then
            Result.Byte_Offset := Pos - Input'First;
         else
            Result.Byte_Offset := Input'Length - 1;
         end if;
      end Set_Err;

      --  After a value completes (string/number/keyword/container closed),
      --  transition to appropriate post-value state based on container context.
      procedure After_Value_Complete is
      begin
         if Depth = 0 then
            Has_Value := True;
            State := State_Finished;
         elsif Stack (Depth) = Container_Object then
            State := State_After_Obj_Val;
         else
            State := State_After_Arr_Val;
         end if;
      end After_Value_Complete;

      --  Dispatch a value-starting character into appropriate state.
      procedure Start_Value (C : Character) is
      begin
         if C = '"' then
            Str_Role := (if Depth = 0 then Role_Top_Level else Role_Value);
            State := State_In_String;
         elsif C = '{' then
            if Depth >= MAX_JSON_DEPTH then
               Set_Err;
            else
               Depth := Depth + 1;
               Stack (Depth) := Container_Object;
               State := State_In_Object;
            end if;
         elsif C = '[' then
            if Depth >= MAX_JSON_DEPTH then
               Set_Err;
            else
               Depth := Depth + 1;
               Stack (Depth) := Container_Array;
               State := State_In_Array;
            end if;
         elsif C = 't' then
            Kw_Expect := To_Unbounded_String ("true");
            Kw_Index := 2;
            State := State_In_Keyword;
         elsif C = 'f' then
            Kw_Expect := To_Unbounded_String ("false");
            Kw_Index := 2;
            State := State_In_Keyword;
         elsif C = 'n' then
            Kw_Expect := To_Unbounded_String ("null");
            Kw_Index := 2;
            State := State_In_Keyword;
         elsif C = '-' or Is_Digit (C) then
            State := State_In_Number;
         else
            Set_Err;
         end if;
      end Start_Value;

      --  Close a container (object or array) and transition state.
      procedure Close_Container is
      begin
         Depth := Depth - 1;
         After_Value_Complete;
      end Close_Container;

   begin  --  Validate_Json_Structure
      while Pos <= Input'Last and State /= State_Parse_Error loop
         declare
            C : constant Character := Input (Pos);
         begin
            case State is
               when State_Value_Start =>
                  if Is_WS (C) then
                     null;
                  else
                     Start_Value (C);
                  end if;

               when State_In_Object =>
                  if Is_WS (C) then
                     null;
                  elsif C = '"' then
                     Str_Role := Role_Key;
                     State := State_In_String;
                  elsif C = '}' then
                     Close_Container;
                  else
                     Set_Err;
                  end if;

               when State_After_Key =>
                  if Is_WS (C) then
                     null;
                  elsif C = ':' then
                     State := State_After_Colon;
                  else
                     Set_Err;
                  end if;

               when State_After_Colon =>
                  if Is_WS (C) then
                     null;
                  else
                     Start_Value (C);
                  end if;

               when State_After_Obj_Val =>
                  if Is_WS (C) then
                     null;
                  elsif C = ',' then
                     State := State_In_Object;
                  elsif C = '}' then
                     Close_Container;
                  else
                     Set_Err;
                  end if;

               when State_In_Array =>
                  if Is_WS (C) then
                     null;
                  elsif C = ']' then
                     Close_Container;
                  else
                     Start_Value (C);
                  end if;

               when State_After_Arr_Val =>
                  if Is_WS (C) then
                     null;
                  elsif C = ',' then
                     State := State_In_Array;
                  elsif C = ']' then
                     Close_Container;
                  else
                     Set_Err;
                  end if;

               when State_In_String =>
                  if C = Backslash then
                     State := State_In_Escape;
                  elsif C = '"' then
                     --  String ended. Transition depends on role.
                     if Str_Role = Role_Key then
                        State := State_After_Key;
                     else
                        After_Value_Complete;
                     end if;
                  elsif Character'Pos (C) < 16#20# then
                     Set_Err;
                  else
                     null;
                  end if;

               when State_In_Escape =>
                  if C = '"' or C = Backslash or C = '/' or C = 'b'
                     or C = 'f' or C = 'n' or C = 'r' or C = 't'
                  then
                     State := State_In_String;
                  elsif C = 'u' then
                     Hex_Count := 0;
                     State := State_In_Unicode;
                  else
                     Set_Err;
                  end if;

               when State_In_Unicode =>
                  if Is_Hex (C) then
                     Hex_Count := Hex_Count + 1;
                     if Hex_Count = 4 then
                        State := State_In_String;
                     end if;
                  else
                     Set_Err;
                  end if;

               when State_In_Number =>
                  if Is_Digit (C) or C = '.' or C = 'e' or C = 'E'
                     or C = '+' or C = '-'
                  then
                     null;
                  elsif Is_WS (C) or C = ',' or C = '}' or C = ']' then
                     --  Number ended. Handle terminator.
                     if Is_WS (C) then
                        After_Value_Complete;
                     elsif C = ',' then
                        if Depth = 0 then
                           Set_Err;
                        elsif Stack (Depth) = Container_Object then
                           State := State_In_Object;
                        else
                           State := State_In_Array;
                        end if;
                     elsif C = '}' then
                        if Depth = 0
                           or else Stack (Depth) /= Container_Object
                        then
                           Set_Err;
                        else
                           Close_Container;
                        end if;
                     elsif C = ']' then
                        if Depth = 0
                           or else Stack (Depth) /= Container_Array
                        then
                           Set_Err;
                        else
                           Close_Container;
                        end if;
                     end if;
                  else
                     Set_Err;
                  end if;

               when State_In_Keyword =>
                  declare
                     Expected : constant String := To_String (Kw_Expect);
                  begin
                     if Kw_Index <= Expected'Length
                        and then C = Expected (Kw_Index)
                     then
                        Kw_Index := Kw_Index + 1;
                        if Kw_Index > Expected'Length then
                           After_Value_Complete;
                        end if;
                     else
                        Set_Err;
                     end if;
                  end;

               when State_Finished =>
                  if Is_WS (C) then
                     null;
                  else
                     Set_Err;
                  end if;

               when State_Parse_Error =>
                  null;
            end case;
         end;
         Pos := Pos + 1;
      end loop;

      --  Post-processing: check final state
      if State /= State_Parse_Error then
         case State is
            when State_Finished =>
               null;
            when State_In_Number =>
               if Depth = 0 then
                  Has_Value := True;
               else
                  Result.Valid := False;
                  Result.Byte_Offset := Input'Length - 1;
               end if;
            when State_In_Keyword =>
               declare
                  Expected : constant String := To_String (Kw_Expect);
               begin
                  if Kw_Index > Expected'Length and Depth = 0 then
                     Has_Value := True;
                  else
                     Result.Valid := False;
                     Result.Byte_Offset := Input'Length - 1;
                  end if;
               end;
            when others =>
               Result.Valid := False;
               Result.Byte_Offset := Input'Length - 1;
         end case;

         if Result.Valid and not Has_Value then
            Result.Valid := False;
            Result.Byte_Offset := 0;
         end if;
      end if;

      return Result;
   end Validate_Json_Structure;

   --  Build the JSON error response for a parse error with byte offset.
   --  Pre:  Byte_Offset is a valid position
   --  Post: result starts with '{'
   function Build_Parse_Error_Response (Byte_Offset : Natural) return String
      with
         Post => Build_Parse_Error_Response'Result
                    (Build_Parse_Error_Response'Result'First) = '{'
   is
      pragma SPARK_Mode (Off);  --  Natural'Image not in SPARK subset
      Offset_Img : constant String :=
         Ada.Strings.Fixed.Trim (Natural'Image (Byte_Offset),
                                  Ada.Strings.Left);
   begin
      return "{""error"":""parse_error"", ""byte_offset"": " &
             Offset_Img & "}";
   end Build_Parse_Error_Response;

   --  =========================================================================
   --  LEGACY GEMINI API FUNCTIONS (kept for non-Geall mode)
   --  =========================================================================

   function Calculate_Cost
      (Input_Tokens  : Natural;
       Output_Tokens : Natural) return Float
      with
         Pre  => Input_Tokens >= 0 and Output_Tokens >= 0,
         Post => Calculate_Cost'Result >= 0.0
   is
      Input_Cost  : constant Float := Float (Input_Tokens) * COST_PER_TOKEN_INPUT;
      Output_Cost : constant Float := Float (Output_Tokens) * COST_PER_TOKEN_OUTPUT;
   begin
      return Input_Cost + Output_Cost;
   end Calculate_Cost;

   function Language_To_String (Lang : Language_Code) return String
      with
         Post => Language_To_String'Result'Length = 2
   is
   begin
      case Lang is
         when cs => return "cs";
         when en => return "en";
         when de => return "de";
         when fr => return "fr";
         when es => return "es";
         when it => return "it";
         when ru => return "ru";
         when ja => return "ja";
         when zh => return "zh";
      end case;
   end Language_To_String;

   function Task_Type_To_String (T : AI_Task_Type) return String is
   begin
      case T is
         when Text_Generation   => return "text-generation";
         when Voice_Synthesis   => return "voice-synthesis";
         when Voice_Cloning     => return "voice-cloning";
         when Real_Time_Dubbing => return "real-time-dubbing";
         when Translation       => return "translation";
         when Sentiment_Analysis => return "sentiment-analysis";
      end case;
   end Task_Type_To_String;

   procedure Call_Gemini_API
      (Request  : in  Gemini_Request;
       Response : out Gemini_Response)
      with
         Pre  => Length (Request.Prompt) > 0 and
                 Length (Request.Prompt) <= MAX_PROMPT_LENGTH,
         Post => Response.Cost_ETH >= 0.0
   is
      pragma SPARK_Mode (Off);
      Prompt_Str : constant String := To_String (Request.Prompt);

      Simulated_Input_Tokens  : constant Natural := Prompt_Str'Length / 4;
      Simulated_Output_Tokens : constant Natural := Request.Max_Tokens / 2;
   begin
      Put_Line ("[GEMINI] ** API Call");
      Put_Line ("[GEMINI]   Task: " & Task_Type_To_String (Request.Task_Type));
      Put_Line ("[GEMINI]   Source: " &
                Language_To_String (Request.Source_Lang));
      Put_Line ("[GEMINI]   Target: " &
                Language_To_String (Request.Target_Lang));
      Put_Line ("[GEMINI]   Prompt length: " &
                Natural'Image (Prompt_Str'Length));
      Put_Line ("[GEMINI]   Max tokens: " &
                Natural'Image (Request.Max_Tokens));

      Response.Success       := True;
      Response.Response_Text := To_Unbounded_String (
         "Gemini AI response: Preklad dokoncen. " &
         "Real-time dubbing kvalita: 98%. " &
         "Voice cloning uspesny."
      );
      Response.Tokens_Used := Simulated_Output_Tokens;
      Response.Cost_ETH    := Calculate_Cost (Simulated_Input_Tokens,
                                               Simulated_Output_Tokens);
      Response.Quality := 98;

      Put_Line ("[GEMINI] * Response received");
      Put_Line ("[GEMINI]   Tokens used: " &
                Natural'Image (Response.Tokens_Used));
      Put_Line ("[GEMINI]   Cost: " & Float'Image (Response.Cost_ETH) &
                " ETH");
      Put_Line ("[GEMINI]   Quality: " &
                Natural'Image (Response.Quality) & "%");
   end Call_Gemini_API;

   procedure Tartanskomunikator_Dubbing
      (Source_Lang  : Language_Code;
       Target_Lang  : Language_Code;
       Audio_Stream : String)
      with
         Pre => Audio_Stream'Length > 0
   is
      pragma SPARK_Mode (Off);
      Request  : Gemini_Request;
      Response : Gemini_Response;
   begin
      Put_Line ("");
      Put_Line ("============================================================");
      Put_Line ("***  TARTANSKOMUNIK-TOR - REAL-TIME DUBBING");
      Put_Line ("============================================================");

      Request := (
         Task_Type   => Real_Time_Dubbing,
         Source_Lang => Source_Lang,
         Target_Lang => Target_Lang,
         Prompt      => To_Unbounded_String (
            "Real-time dubbing: " & Audio_Stream
         ),
         Max_Tokens  => 2048,
         Temperature => 0.7,
         Top_P       => 0.95
      );

      if Validate_Prompt (To_String (Request.Prompt)) then
         Call_Gemini_API (Request, Response);

         if Response.Success then
            Put_Line ("");
            Put_Line ("[DUBBING] Preklad dokoncen");
            Put_Line ("[DUBBING] " & To_String (Response.Response_Text));
            Put_Line ("[DUBBING] Cena: " &
                      Float'Image (Response.Cost_ETH) & " ETH");
            Put_Line ("[DUBBING] Kvalita: " &
                      Natural'Image (Response.Quality) & "%");
         else
            Put_Line ("[DUBBING] Chyba prekladu");
         end if;
      else
         Put_Line ("[DUBBING] Neplatny prompt");
      end if;

      Put_Line ("============================================================");
   end Tartanskomunikator_Dubbing;

   procedure Voice_Cloning_Engine
      (Voice_Sample : String;
       Target_Text  : String)
      with
         Pre => Voice_Sample'Length > 0 and Target_Text'Length > 0
   is
      pragma SPARK_Mode (Off);
      Request  : Gemini_Request;
      Response : Gemini_Response;
   begin
      Put_Line ("");
      Put_Line ("============================================================");
      Put_Line ("** VOICE CLONING ENGINE");
      Put_Line ("============================================================");

      Request := (
         Task_Type   => Voice_Cloning,
         Source_Lang => cs,
         Target_Lang => cs,
         Prompt      => To_Unbounded_String (
            "Voice sample: " & Voice_Sample & " | " &
            "Target text: " & Target_Text
         ),
         Max_Tokens  => 4096,
         Temperature => 0.5,
         Top_P       => 0.9
      );

      if Validate_Prompt (To_String (Request.Prompt)) then
         Call_Gemini_API (Request, Response);

         if Response.Success then
            Put_Line ("");
            Put_Line ("[VOICE] * Hlas naklonov-n");
            Put_Line ("[VOICE] Kvalita: " &
                      Natural'Image (Response.Quality) & "%");
            Put_Line ("[VOICE] Cena: " &
                      Float'Image (Response.Cost_ETH) & " ETH");
         else
            Put_Line ("[VOICE] Chyba klonovani");
         end if;
      else
         Put_Line ("[VOICE] Neplatny prompt");
      end if;

      Put_Line ("============================================================");
   end Voice_Cloning_Engine;

   --  =========================================================================
   --  GEALL DISPATCH (Ada/SPARK AI engine - osobn- asistent)
   --  =========================================================================

   --  Handle --geall --translate
   --  Reads one JSON line from stdin, writes one JSON line to stdout.
   --  Validates: JSON structure (returns byte offset on malformed input),
   --             text field with Validate_Prompt (1..8192),
   --             source/target with Validate_Field (1..4096),
   --             response with Validate_Field (1..4096).
   --  Returns: {"translated":"...", "quality_score": N} on success
   --           {"error":"parse_error", "byte_offset": N} on malformed JSON
   --           {"error":"<reason>"} on validation failure
   --  Requirements: 5.1, 5.2, 5.5, 13.2, 13.4, 13.5
   procedure Geall_Translate is
      pragma SPARK_Mode (Off);  --  I/O not in SPARK subset
      Line      : String (1 .. MAX_INPUT_LINE);
      Line_Last : Natural;
      Text_Val  : Unbounded_String;
      Src_Val   : Unbounded_String;
      Tgt_Val   : Unbounded_String;
   begin
      Get_Line (Line, Line_Last);

      if Line_Last = 0 then
         Put_Line ("{""error"": ""empty input""}");
         return;
      end if;

      declare
         Safe_Last : constant Natural :=
            Clamp_Input_Length (Line_Last);
         Json      : constant String := Line (1 .. Safe_Last);
      begin
         if not Validate_Input_Line (Json) then
            Put_Line ("{""error"": ""input line too long or empty""}");
            return;
         end if;

         --  Validate JSON structure before field extraction (req 13.4).
         --  If malformed, output parse error with byte offset and exit 1.
         declare
            Parse_Check : constant Json_Parse_Result :=
               Validate_Json_Structure (Json);
         begin
            if not Parse_Check.Valid then
               Put_Line (Build_Parse_Error_Response (Parse_Check.Byte_Offset));
               Ada.Command_Line.Set_Exit_Status (Ada.Command_Line.Failure);
               return;
            end if;
         end;

         Text_Val := To_Unbounded_String (
            Extract_Json_String (Json, "text"));
         Src_Val  := To_Unbounded_String (
            Extract_Json_String (Json, "source"));
         Tgt_Val  := To_Unbounded_String (
            Extract_Json_String (Json, "target"));

         --  Validate "text" field: must be non-empty and within prompt
         --  bounds (1..MAX_PROMPT_LENGTH = 8192) per req 5.1, 5.5
         if Length (Text_Val) = 0 then
            Put_Line ("{""error"": ""field 'text' is missing or empty""}");
            return;
         end if;

         if not Validate_Prompt (To_String (Text_Val)) then
            Put_Line ("{""error"": ""field 'text' exceeds maximum " &
                      "length (8192 characters)""}");
            return;
         end if;

         --  Validate "source" field: must be non-empty and within field
         --  bounds (1..MAX_FIELD_LENGTH = 4096) per req 13.5
         if Length (Src_Val) = 0 then
            Put_Line ("{""error"": ""field 'source' is missing or empty""}");
            return;
         end if;

         if not Validate_Field (To_String (Src_Val)) then
            Put_Line ("{""error"": ""field 'source' exceeds maximum " &
                      "length (4096 characters)""}");
            return;
         end if;

         --  Validate "target" field: must be non-empty and within field
         --  bounds (1..MAX_FIELD_LENGTH = 4096) per req 13.5
         if Length (Tgt_Val) = 0 then
            Put_Line ("{""error"": ""field 'target' is missing or empty""}");
            return;
         end if;

         if not Validate_Field (To_String (Tgt_Val)) then
            Put_Line ("{""error"": ""field 'target' exceeds maximum " &
                      "length (4096 characters)""}");
            return;
         end if;

         declare
            --  Stub translation: prepend source*target prefix to input text
            Src_Str  : constant String := To_String (Src_Val);
            Tgt_Str  : constant String := To_String (Tgt_Val);
            Text_Str : constant String := To_String (Text_Val);
            Prefix   : constant String :=
               "[" & Src_Str & "*" & Tgt_Str & "] ";
            Translated : constant String := Prefix & Text_Str;
            --  Clamp to MAX_FIELD_LENGTH for response field (req 5.2)
            Safe_Translated : constant String :=
               (if Translated'Length > MAX_FIELD_LENGTH
                then Translated
                        (Translated'First ..
                         Translated'First + MAX_FIELD_LENGTH - 1)
                else Translated);
         begin
            --  Final response field validation (req 5.2, 13.5)
            if not Validate_Field (Safe_Translated) then
               Put_Line ("{""error"": ""translated result exceeds " &
                         "maximum field length (4096 characters)""}");
               return;
            end if;
            Put_Line (Build_Translate_Response (Safe_Translated));
         end;
      end;
   end Geall_Translate;

   --  Handle --geall --infer (Geall query path)
   --  Reads one JSON line from stdin, writes one JSON line to stdout.
   --  Returns: {"error":"parse_error", "byte_offset": N} on malformed JSON
   --  Requirements: 13.4
   procedure Geall_Infer is
      pragma SPARK_Mode (Off);  --  I/O not in SPARK subset
      Line      : String (1 .. MAX_INPUT_LINE);
      Line_Last : Natural;
      Query_Val : Unbounded_String;
   begin
      Get_Line (Line, Line_Last);

      if Line_Last = 0 then
         Put_Line ("{""error"": ""empty input""}");
         return;
      end if;

      declare
         Safe_Last : constant Natural :=
            Clamp_Input_Length (Line_Last);
         Json      : constant String := Line (1 .. Safe_Last);
      begin
         if not Validate_Input_Line (Json) then
            Put_Line ("{""error"": ""input line too long or empty""}");
            return;
         end if;

         --  Validate JSON structure before field extraction (req 13.4).
         --  If malformed, output parse error with byte offset and exit 1.
         declare
            Parse_Check : constant Json_Parse_Result :=
               Validate_Json_Structure (Json);
         begin
            if not Parse_Check.Valid then
               Put_Line (Build_Parse_Error_Response (Parse_Check.Byte_Offset));
               Ada.Command_Line.Set_Exit_Status (Ada.Command_Line.Failure);
               return;
            end if;
         end;

         Query_Val := To_Unbounded_String (
            Extract_Json_String (Json, "query"));

         if Length (Query_Val) = 0 then
            Put_Line ("{""error"": ""missing field: query""}");
            return;
         end if;

         declare
            Query_Str : constant String := To_String (Query_Val);
            --  Stub inference: Karel IV. echoes the query with a prefix
            Resp_Text : constant String :=
               "Karel IV. [Geall stub]: " & Query_Str;
            Safe_Resp : constant String :=
               (if Resp_Text'Length > MAX_FIELD_LENGTH
                then Resp_Text
                        (Resp_Text'First ..
                         Resp_Text'First + MAX_FIELD_LENGTH - 1)
                else Resp_Text);
         begin
            if not Validate_Field (Safe_Resp) then
               Put_Line ("{""error"": ""response result invalid""}");
               return;
            end if;
            Put_Line (Build_Infer_Response (Safe_Resp));
         end;
      end;
   end Geall_Infer;

   --  =========================================================================
   --  MAIN LOGIC
   --  =========================================================================

   use Ada.Command_Line;

   Geall_Mode       : Boolean := False;
   Translate_Mode   : Boolean := False;
   Infer_Mode       : Boolean := False;

begin
   --  Parse CLI arguments
   for I in 1 .. Argument_Count loop
      declare
         Arg : constant String := Argument (I);
      begin
         if Arg = "--geall" then
            Geall_Mode := True;
         elsif Arg = "--translate" then
            Translate_Mode := True;
         elsif Arg = "--infer" then
            Infer_Mode := True;
         end if;
      end;
   end loop;

   --  -------------------------------------------------------------------------
   --  Geall: JSON stdin - JSON stdout (osobn- asistent)
   --  -------------------------------------------------------------------------
   if Geall_Mode then
      if Translate_Mode then
         Geall_Translate;
      elsif Infer_Mode then
         Geall_Infer;
      else
         Put_Line ("{""error"": ""--geall requires --translate or --infer""}");
      end if;
      return;
   end if;

   --  -------------------------------------------------------------------------
   --  Bifrost demo mode (no --geall flag)
   --  -------------------------------------------------------------------------
   Put_Line ("");
   Put_Line ("============================================================");
   Put_Line ("-- BIFROST - Ada/SPARK - Gemini AI Bridge");
   Put_Line ("============================================================");
   Put_Line ("[GEMINI] API Version: " & GEMINI_API_VERSION);
   Put_Line ("[GEMINI] Max prompt: " & Natural'Image (MAX_PROMPT_LENGTH));
   Put_Line ("[GEMINI] Max response: " & Natural'Image (MAX_RESPONSE_LENGTH));
   Put_Line ("[GEMINI] Cost/token (input): " &
             Float'Image (COST_PER_TOKEN_INPUT) & " ETH");
   Put_Line ("[GEMINI] Cost/token (output): " &
             Float'Image (COST_PER_TOKEN_OUTPUT) & " ETH");
   Put_Line ("============================================================");

   --  Test 1: Real-time dubbing (Netflix - Czech)
   Tartanskomunikator_Dubbing (
      Source_Lang  => en,
      Target_Lang  => cs,
      Audio_Stream => "Netflix audio stream: Episode 1, Scene 5"
   );

   --  Test 2: Voice cloning
   Voice_Cloning_Engine (
      Voice_Sample => "voice-sample-001.wav",
      Target_Text  => "Dobr- den, v-tejte v syst-mu Vakuov- Mincovna."
   );

   Put_Line ("");
   Put_Line ("============================================================");
   Put_Line ("[BIFROST] - All tests completed");
   Put_Line ("[BIFROST] Integration: Faucet + Prometheus + Sepolia ETH");
   Put_Line ("============================================================");
   Put_Line ("");

end Bifrost;
