pragma SPARK_Mode (On);

package body Sign_Language_Stream_Synchronizer is

   procedure Initialize_Synchronizer
     (State : out Sync_State)
   is
   begin
      State.Stream_Active     := True;
      State.Current_Timestamp := 0;
      State.Current_Frame     := 0;
      State.Active_Gesture_ID := 1;
      State.Measured_Latency  := 0;
      State.Dropped_Frames    := 0;
      State.Is_Synchronized   := True;
   end Initialize_Synchronizer;

   procedure Advance_Stream_Frame
     (State        : in out Sync_State;
      Delta_Ms     : in     Delta_Ms_Type;
      New_Gesture  : in     Gesture_ID_Type;
      Frame_Lag_Ms : in     Lag_Ms_Type;
      Success      : out    Boolean)
   is
   begin
      if State.Current_Timestamp <= 3_600_000 - Timestamp_Ms_Type (Delta_Ms) and then
         State.Current_Frame < 216_000
      then
         State.Current_Timestamp := State.Current_Timestamp + Timestamp_Ms_Type (Delta_Ms);
         State.Current_Frame     := State.Current_Frame + 1;
         State.Active_Gesture_ID := New_Gesture;

         if Frame_Lag_Ms > 50 then
            State.Measured_Latency := 50;
            if State.Dropped_Frames < 1_000 then
               State.Dropped_Frames := State.Dropped_Frames + 1;
            end if;
            State.Is_Synchronized := False;
         else
            State.Measured_Latency := Latency_Ms_Type (Frame_Lag_Ms);
            State.Is_Synchronized  := True;
         end if;

         Success := True;
      else
         Success := False;
      end if;
   end Advance_Stream_Frame;

end Sign_Language_Stream_Synchronizer;
