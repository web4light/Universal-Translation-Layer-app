--  =============================================================================
--  Asterisk Gateway — Merkle State Accumulator Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  =============================================================================

package body Merkle_State_Accumulator with
  SPARK_Mode => On
is

   Genesis_Root : constant Accumulator_Word := 16#C0DE_2026#;
   FNV_Prime    : constant Accumulator_Word := 16#0100_0193#;
   Golden_Const : constant Accumulator_Word := 16#9E37_79B9#;

   procedure Initialize_Accumulator
     (State : out Checkpoint_State)
   is
   begin
      State := (Current_Root => Genesis_Root,
                Step_Index   => 0,
                Is_Finalized => False);
   end Initialize_Accumulator;

   procedure Accumulate_Step
     (State       : in out Checkpoint_State;
      Step_Digest : in     Accumulator_Word;
      Success     : out    Boolean)
   is
   begin
      if not State.Is_Finalized and then State.Step_Index < Max_Steps then
         State.Current_Root :=
           ((State.Current_Root xor Step_Digest) * FNV_Prime) + Golden_Const;
         State.Step_Index   := State.Step_Index + 1;
         Success            := True;
      else
         Success := False;
      end if;
   end Accumulate_Step;

   procedure Finalize_Commitment
     (State       : in out Checkpoint_State;
      Final_Root  : out    Accumulator_Word;
      Total_Steps : out    Step_Count;
      Success     : out    Boolean)
   is
   begin
      if not State.Is_Finalized and then State.Step_Index > 0 then
         State.Is_Finalized := True;
         Final_Root         := State.Current_Root;
         Total_Steps        := State.Step_Index;
         Success            := True;
      else
         Final_Root  := 0;
         Total_Steps := 0;
         Success     := False;
      end if;
   end Finalize_Commitment;

end Merkle_State_Accumulator;
