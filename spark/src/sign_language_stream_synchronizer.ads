pragma SPARK_Mode (On);

package Sign_Language_Stream_Synchronizer is

   type Timestamp_Ms_Type is range 0 .. 3_600_000; -- up to 1 hour stream
   type Frame_Index_Type is range 0 .. 216_000;   -- 60 fps * 3600 sec
   type Gesture_ID_Type is range 1 .. 256;
   type Latency_Ms_Type is range 0 .. 50;         -- strictly bounded <= 50ms latency
   type Delta_Ms_Type is range 1 .. 100;
   type Lag_Ms_Type is range 0 .. 200;

   type Sync_State is record
      Stream_Active      : Boolean;
      Current_Timestamp  : Timestamp_Ms_Type;
      Current_Frame      : Frame_Index_Type;
      Active_Gesture_ID  : Gesture_ID_Type;
      Measured_Latency   : Latency_Ms_Type;
      Dropped_Frames     : Natural range 0 .. 1_000;
      Is_Synchronized    : Boolean;
   end record;

   procedure Initialize_Synchronizer
     (State : out Sync_State)
   with
     Global => null,
     Depends => (State => null),
     Post =>
       State.Stream_Active and then
       State.Current_Timestamp = 0 and then
       State.Current_Frame = 0 and then
       State.Active_Gesture_ID = 1 and then
       State.Measured_Latency = 0 and then
       State.Dropped_Frames = 0 and then
       State.Is_Synchronized;

   procedure Advance_Stream_Frame
     (State        : in out Sync_State;
      Delta_Ms     : in     Delta_Ms_Type;
      New_Gesture  : in     Gesture_ID_Type;
      Frame_Lag_Ms : in     Lag_Ms_Type;
      Success      : out    Boolean)
   with
     Global => null,
     Depends =>
       (State   =>+ (Delta_Ms, New_Gesture, Frame_Lag_Ms),
        Success => (State, Delta_Ms)),
     Pre => State.Stream_Active,
     Post =>
       (if Success then
          State.Stream_Active and then
          State.Current_Timestamp = State'Old.Current_Timestamp + Timestamp_Ms_Type (Delta_Ms) and then
          State.Current_Frame = State'Old.Current_Frame + 1 and then
          State.Active_Gesture_ID = New_Gesture and then
          State.Measured_Latency <= 50
        else
          State = State'Old);

end Sign_Language_Stream_Synchronizer;
