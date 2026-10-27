pragma SPARK_Mode (On);

package StarsChain_Consensus is

   Max_Validators : constant := 100;
   Min_Quorum_Pct : constant := 67; -- 2/3 většina (BFT)

   subtype Validator_Count is Natural range 0 .. Max_Validators;
   subtype Epoch_Id        is Natural range 0 .. 1_000_000;
   subtype Slot_Id         is Natural range 0 .. 31;

   type Consensus_State is (State_Proposing, State_Voting, State_Finalized, State_Reorganizing);

   type Consensus_Round is record
      Epoch            : Epoch_Id;
      Slot             : Slot_Id;
      Active_Nodes     : Validator_Count;
      Votes_Received   : Validator_Count;
      State            : Consensus_State;
      Block_Hash       : Natural;
      Is_Justified     : Boolean;
   end record;

   -- Inicializace nové konsensuální epochy
   procedure Start_Epoch (
      Round        : in out Consensus_Round;
      New_Epoch    : in     Epoch_Id;
      Active_Nodes : in     Validator_Count
   )
   with
      Global  => null,
      Depends => (Round =>+ (New_Epoch, Active_Nodes)),
      Pre     => New_Epoch > Round.Epoch and Active_Nodes >= 3,
      Post    => Round.Epoch = New_Epoch and then
                 Round.Active_Nodes = Active_Nodes and then
                 Round.Votes_Received = 0 and then
                 Round.State = State_Proposing and then
                 not Round.Is_Justified;

   -- Zaznamenání hlasu validátora s kontrolou kvóra
   procedure Cast_Vote (
      Round        : in out Consensus_Round;
      Vote_Weight  : in     Positive;
      Is_Finalized :    out Boolean
   )
   with
      Global  => null,
      Depends => (
         Round        =>+ Vote_Weight,
         Is_Finalized => (Round, Vote_Weight)
      ),
      Pre     => Round.Active_Nodes > 0 and then
                 Round.Votes_Received <= Round.Active_Nodes,
      Post    => Round.Votes_Received >= Round.Votes_Received'Old and then
                 (if Is_Finalized then (Round.State = State_Finalized and Round.Is_Justified) else True);

end StarsChain_Consensus;
