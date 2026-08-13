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

end Judge_Lab;
