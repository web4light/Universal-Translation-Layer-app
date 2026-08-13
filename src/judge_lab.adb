-- ============================================================
--  Judge Lab — Implementation
--  "Iustitia omnibus." (Spravedlnost vsem.)
-- ============================================================

pragma SPARK_Mode (On);

package body Judge_Lab is

   -- =========================================================
   --  File_Case
   -- =========================================================

   procedure File_Case (C    : in out Court_Case;
                        Kind : Case_Kind;
                        Prio : Case_Priority) is
   begin
      C.Kind := Kind;
      C.Priority := Prio;
      C.Status := Under_Review;
      -- Default: NEvinny dokud neprokaze opak? NE.
      -- V Judge Lab: VINNY dokud neprokaze nevinu.
      -- Bezpecnostni princip.
      C.Decision := NON;
   end File_Case;

   -- =========================================================
   --  Render_Verdict
   -- =========================================================

   procedure Render_Verdict (C      : in out Court_Case;
                             Result : Verdict;
                             Reason : Verdict_Reason) is
   begin
      C.Decision := Result;
      C.Reason := Reason;
      C.Status := Verdict_Made;
   end Render_Verdict;

   -- =========================================================
   --  Enforce
   -- =========================================================

   procedure Enforce (C : in out Court_Case) is
   begin
      C.Status := Enforced;
      C.Enforced := True;
      -- Tady v I/O casti: smazat agenta, zablokovat contract, atd.
   end Enforce;

   -- =========================================================
   --  Appeal
   -- =========================================================

   procedure Appeal (C : in out Court_Case) is
   begin
      -- Jedno odvolani. Justyna znovu posoudí.
      -- Ale uz vi ze to je odvolani → prisnejsi pohled.
      C.Status := Under_Review;
      C.Appealed := True;
   end Appeal;

   -- =========================================================
   --  Archive
   -- =========================================================

   procedure Archive (C : in out Court_Case) is
   begin
      C.Status := Archived;
   end Archive;

   -- =========================================================
   --  Count_Case
   -- =========================================================

   procedure Count_Case (Counter : in out Case_Counter) is
   begin
      Counter := Counter + 1;
   end Count_Case;

   -- =========================================================
   --  Conviction_Rate
   -- =========================================================

   function Conviction_Rate (SIC_Count : Case_Counter;
                             Total     : Case_Counter) return Natural is
      Rate : Natural;
   begin
      Rate := Natural (SIC_Count) * 100 / Natural (Total);
      if Rate > 100 then
         Rate := 100;
      end if;
      return Rate;
   end Conviction_Rate;

   -- =========================================================
   --  License_Compatible — formalni matice
   -- =========================================================

   function License_Compatible (A, B : License_Type) return Boolean is
   begin
      -- Charter je kompatibilni se vsim (nase pravidla)
      if A = Charter or B = Charter then
         return True;
      end if;

      -- Public Domain je kompatibilni se vsim
      if A = Public_Domain or B = Public_Domain then
         return True;
      end if;

      -- Stejne licence jsou kompatibilni
      if A = B then
         return True;
      end if;

      -- Permisivni mezi sebou OK
      if A in Apache_2_0 | MIT | BSD_3
         and B in Apache_2_0 | MIT | BSD_3
      then
         return True;
      end if;

      -- Permisivni + copyleft = OK
      if (A in Apache_2_0 | MIT | BSD_3 and B in GPL_3 | LGPL_3 | MPL_2)
         or (B in Apache_2_0 | MIT | BSD_3 and A in GPL_3 | LGPL_3 | MPL_2)
      then
         return True;
      end if;

      -- LGPL + GPL OK
      if (A = LGPL_3 and B = GPL_3) or (A = GPL_3 and B = LGPL_3) then
         return True;
      end if;

      -- Vse ostatni = NE (Proprietary + copyleft, atd.)
      return False;
   end License_Compatible;

   -- =========================================================
   --  Verify_Standard_700
   --  1 mince = 12g stribra. Bod.
   -- =========================================================

   function Verify_Standard_700 (Coins : Natural;
                                 Silver_Grams : Natural) return Verdict is
   begin
      if Silver_Grams >= Coins * Standard_700_Grams then
         return SIC;
      else
         return NON;
      end if;
   end Verify_Standard_700;

end Judge_Lab;
