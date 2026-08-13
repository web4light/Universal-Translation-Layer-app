-- ============================================================
--  PJAY Lexer — Lexiographus Linguae PJAY
--
--  Tokenizace PJAY zdrojoveho kodu.
--  PJAY se kompiluje do Ada/SPARK → gnatprove verifikace.
--
--  Klicova slova (Lingua Latina):
--    procedura, incipit, finis, si, tum, alias
--    Hoc_est_via, Locutus_sum, Ego_sum_Groot, Latratus
--
--  "Hoc est via." — This is the way.
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0 (Rebirth Phoenix Foundation Charter)
--  GPL-free. Zadna GNU.
-- ============================================================

pragma SPARK_Mode (On);

package PJAY_Lexer is

   -- Maximalni delka tokenu
   Max_Token_Len : constant := 128;
   subtype Token_Length is Natural range 0 .. Max_Token_Len;

   -- Maximalni pocet tokenu na radek
   Max_Tokens_Per_Line : constant := 64;

   -- Typy tokenu
   type Token_Kind is
     (-- Klicova slova (Lingua Latina)
      Tok_Procedura,       -- procedura
      Tok_Incipit,         -- incipit (begin)
      Tok_Finis,           -- finis (end)
      Tok_Si,              -- si (if)
      Tok_Tum,             -- tum (then)
      Tok_Alias,           -- alias (else)
      Tok_Est,             -- est (is)
      Tok_Finis_Si,        -- finis si (end if)

      -- Mandalorian principia
      Tok_Hoc_Est_Via,     -- "Hoc est via:" (deklarace/config)
      Tok_Locutus_Sum,     -- "Locutus sum:" (executio/akce)
      Tok_Ego_Sum_Groot,   -- "Ego sum Groot:" (boolean/rozhodnuti)
      Tok_Latratus,        -- "Latratus!" (alert/verifikace)

      -- Hodnoty
      Tok_SIC,             -- SIC (true)
      Tok_NON,             -- NON (false)
      Tok_Identifier,      -- nazev (promenna, funkce)
      Tok_String_Literal,  -- "text"
      Tok_Number,          -- cislo
      Tok_Assign,          -- :=
      Tok_Comma,           -- ,
      Tok_Semicolon,       -- ;
      Tok_Open_Paren,      -- (
      Tok_Close_Paren,     -- )
      Tok_Comment,         -- -- komentar
      Tok_EOF,             -- konec souboru
      Tok_Unknown);        -- neznamy

   -- Jeden token
   type Token is record
      Kind   : Token_Kind := Tok_Unknown;
      Length : Token_Length := 0;
      Line   : Positive := 1;
      Column : Positive := 1;
   end record;

   -- Buffer tokenu
   type Token_Array is array (Positive range <>) of Token;
   subtype Token_Buffer is Token_Array (1 .. Max_Tokens_Per_Line);

   -- Vysledek lexingu jednoho radku
   type Lex_Result is record
      Tokens     : Token_Buffer;
      Count      : Natural range 0 .. Max_Tokens_Per_Line := 0;
      Has_Error  : Boolean := False;
      Error_Col  : Positive := 1;
   end record;

   -- Rozpoznej typ tokenu z textu
   function Classify_Word (Word_Len : Token_Length) return Token_Kind
     with Post => Classify_Word'Result in
       Tok_Procedura | Tok_Incipit | Tok_Finis | Tok_Si |
       Tok_Tum | Tok_Alias | Tok_Est | Tok_SIC | Tok_NON |
       Tok_Identifier;

   -- Je znak whitespace?
   function Is_Space (C : Character) return Boolean
     with Post => Is_Space'Result = (C = ' ' or C = ASCII.HT);

   -- Je znak alfanumericky?
   function Is_Alnum (C : Character) return Boolean;

   -- Je to operator/separator?
   function Is_Separator (C : Character) return Boolean;

end PJAY_Lexer;
