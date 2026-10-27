pragma SPARK_Mode (On);

package body StarsChain_Consensus is

   procedure Start_Epoch (
      Round        : in out Consensus_Round;
      New_Epoch    : in     Epoch_Id;
      Active_Nodes : in     Validator_Count
   ) is
   begin
      Round.Epoch          := New_Epoch;
      Round.Slot           := 0;
      Round.Active_Nodes   := Active_Nodes;
      Round.Votes_Received := 0;
      Round.State          := State_Proposing;
      Round.Is_Justified   := False;
   end Start_Epoch;

   procedure Cast_Vote (
      Round        : in out Consensus_Round;
      Vote_Weight  : in     Positive;
      Is_Finalized :    out Boolean
   ) is
      Remaining : constant Natural := Round.Active_Nodes - Round.Votes_Received;
      Added     : Natural;
      Quorum    : Natural;
   begin
      if Remaining = 0 then
         Is_Finalized := (Round.State = State_Finalized and then Round.Is_Justified);
         return;
      end if;

      if Vote_Weight <= Remaining then
         Added := Vote_Weight;
      else
         Added := Remaining;
      end if;

      Round.Votes_Received := Round.Votes_Received + Added;

      -- Výpočet 2/3 BFT hranice (Active_Nodes * 67 / 100)
      Quorum := (Round.Active_Nodes * Min_Quorum_Pct) / 100;
      if Quorum = 0 then
         Quorum := 1;
      end if;

      if Round.Votes_Received >= Quorum then
         Round.State          := State_Finalized;
         Round.Is_Justified   := True;
         Is_Finalized         := True;
      else
         Round.State  := State_Voting;
         Is_Finalized := False;
      end if;
   end Cast_Vote;

end StarsChain_Consensus;
