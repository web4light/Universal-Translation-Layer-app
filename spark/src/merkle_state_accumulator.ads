--  =============================================================================
--  Asterisk Gateway — Merkle State Accumulator
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Cryptographic trajectory accumulator and monotonic audit root committer.
--  Standard 700: Tamper-proof mathematical provenance of agent steps.
--  =============================================================================

package Merkle_State_Accumulator with
  SPARK_Mode => On
is
   Max_Steps : constant := 10_000;
   type Accumulator_Word is mod 2**32;
   subtype Step_Count is Natural range 0 .. Max_Steps;

   type Checkpoint_State is record
      Current_Root : Accumulator_Word;
      Step_Index   : Step_Count;
      Is_Finalized : Boolean;
   end record;

   --  Initializes the accumulator in a pristine genesis state.
   procedure Initialize_Accumulator
     (State : out Checkpoint_State)
   with
     Global => null,
     Depends => (State => null),
     Post => State.Current_Root = 16#C0DE_2026# and then
             State.Step_Index = 0 and then
             not State.Is_Finalized;

   --  Accumulates a step digest into the rolling cryptographic root.
   procedure Accumulate_Step
     (State       : in out Checkpoint_State;
      Step_Digest : in     Accumulator_Word;
      Success     : out    Boolean)
   with
     Global => null,
     Depends => (State   => (State, Step_Digest),
                 Success => State),
     Post => (if Success then
                State.Step_Index = State.Step_Index'Old + 1 and then
                not State.Is_Finalized
              else
                State = State'Old);

   --  Finalizes the checkpoint commitment, sealing it against further mutations.
   procedure Finalize_Commitment
     (State       : in out Checkpoint_State;
      Final_Root  : out    Accumulator_Word;
      Total_Steps : out    Step_Count;
      Success     : out    Boolean)
   with
     Global => null,
     Depends => ((State, Final_Root, Total_Steps, Success) => State),
     Post => (if Success then
                State.Is_Finalized and then
                Final_Root = State.Current_Root and then
                Total_Steps = State.Step_Index
              else
                Final_Root = 0 and then Total_Steps = 0);

end Merkle_State_Accumulator;
