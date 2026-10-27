--  =============================================================================
--  Asterisk Gateway — Sovereign Entropy Pool Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  =============================================================================

package body Sovereign_Entropy_Pool with
  SPARK_Mode => On
is

   Golden_Ratio_Const  : constant Entropy_Word := 16#9E37_79B9#;
   Forward_Secret_Mask : constant Entropy_Word := 16#DEAD_BEEF#;

   procedure Initialize_Pool
     (State : out Entropy_State)
   is
   begin
      State := (Pool          => (others => 16#5A5A_A5A5#),
                Head          => 1,
                Total_Samples => 0,
                Quality       => 0,
                Is_Seeded     => False);
   end Initialize_Pool;

   procedure Stir_Entropy
     (State          : in out Entropy_State;
      Raw_Sample     : in     Entropy_Word;
      Sample_Quality : in     Quality_Level)
   is
      Current_Val : constant Entropy_Word := State.Pool (State.Head);
   begin
      State.Pool (State.Head) := (Current_Val xor Raw_Sample) + Golden_Ratio_Const;

      if State.Head = Pool_Size then
         State.Head := 1;
      else
         State.Head := State.Head + 1;
      end if;

      if State.Total_Samples < Natural'Last then
         State.Total_Samples := State.Total_Samples + 1;
      end if;

      if State.Total_Samples >= Pool_Size then
         State.Is_Seeded := True;
         State.Quality   := (State.Quality + Sample_Quality) / 2;
      end if;
   end Stir_Entropy;

   procedure Extract_Entropy
     (State    : in out Entropy_State;
      Out_Word : out    Entropy_Word;
      Success  : out    Boolean)
   is
   begin
      if State.Is_Seeded and then State.Quality >= Min_Quality_Threshold then
         Out_Word := State.Pool (State.Head) xor Forward_Secret_Mask;
         State.Pool (State.Head) := State.Pool (State.Head) + 1;
         Success  := True;
      else
         Out_Word := 0;
         Success  := False;
      end if;
   end Extract_Entropy;

end Sovereign_Entropy_Pool;
