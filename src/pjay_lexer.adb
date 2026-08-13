-- ============================================================
--  PJAY Lexer — Implementation
--  "Hoc est via."
-- ============================================================

pragma SPARK_Mode (On);

package body PJAY_Lexer is

   -- =========================================================
   --  Classify_Word — rozpoznej klicove slovo
   -- =========================================================

   function Classify_Word (Word_Len : Token_Length) return Token_Kind is
   begin
      -- Klasifikace podle delky (rychly pre-filter)
      -- Plna implementace bude porovnavat znaky
      case Word_Len is
         when 2 =>
            return Tok_Si;        -- "si"
         when 3 =>
            return Tok_SIC;       -- "SIC" nebo "est" nebo "tum" nebo "NON"
         when 5 =>
            return Tok_Alias;     -- "alias" nebo "finis"
         when 7 =>
            return Tok_Incipit;   -- "incipit"
         when 9 =>
            return Tok_Procedura; -- "procedura"
         when others =>
            return Tok_Identifier;
      end case;
   end Classify_Word;

   -- =========================================================
   --  Is_Space
   -- =========================================================

   function Is_Space (C : Character) return Boolean is
   begin
      return C = ' ' or C = ASCII.HT;
   end Is_Space;

   -- =========================================================
   --  Is_Alnum
   -- =========================================================

   function Is_Alnum (C : Character) return Boolean is
   begin
      return C in 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_';
   end Is_Alnum;

   -- =========================================================
   --  Is_Separator
   -- =========================================================

   function Is_Separator (C : Character) return Boolean is
   begin
      return C in '(' | ')' | ',' | ';' | ':' | '!';
   end Is_Separator;

end PJAY_Lexer;
