--  SPARK 2022 Implementation: Sliding_Window_Rate_Tracker
package body Sliding_Window_Rate_Tracker with
  SPARK_Mode => On
is

   procedure Initialize_Tracker (Tracker : out Tracker_State) is
   begin
      Tracker := (Initialized    => True,
                  Head           => 1,
                  Active_Count   => 0,
                  Last_Timestamp => 0,
                  Events         => (others => (Active => False, Time => 0)));
   end Initialize_Tracker;

   procedure Record_Event
     (Tracker : in out Tracker_State;
      Now     : Timestamp_Type;
      Allowed : out Boolean)
   is
      Cutoff      : Timestamp_Type := 0;
      Valid_Count : Event_Count := 0;
   begin
      if Now >= Window_Duration_Ms then
         Cutoff := Now - Window_Duration_Ms;
      end if;

      for I in Event_Index loop
         if Tracker.Events (I).Active and then Tracker.Events (I).Time >= Cutoff then
            Valid_Count := Valid_Count + 1;
         end if;
         pragma Loop_Invariant (Valid_Count <= I);
      end loop;

      Tracker.Last_Timestamp := Now;

      if Valid_Count >= Max_Events_Per_Window then
         Tracker.Active_Count := Valid_Count;
         Allowed := False;
      else
         Tracker.Events (Tracker.Head) := (Active => True, Time => Now);
         if Tracker.Head = Max_Events_Per_Window then
            Tracker.Head := 1;
         else
            Tracker.Head := Tracker.Head + 1;
         end if;
         Tracker.Active_Count := Valid_Count + 1;
         Allowed := True;
      end if;
   end Record_Event;

end Sliding_Window_Rate_Tracker;
