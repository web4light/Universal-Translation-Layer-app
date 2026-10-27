pragma SPARK_Mode (On);

package body Sign_Pose_Validator is

   procedure Validate_Hand_Pose (
      Pose         : in  Hand_Skeleton;
      Min_Conf     : in  Confidence_Val;
      Result       : out Validation_Result;
      Valid_Joints : out Natural
   ) is
      Count         : Natural range 0 .. 21 := 0;
      Failed_Bounds : Boolean := False;
      Failed_Conf   : Boolean := False;
   begin
      for I in Joint_Index loop
         pragma Loop_Invariant (Count <= Natural (I) - 1);
         pragma Loop_Invariant (if not Failed_Bounds and then not Failed_Conf then
                                   Count = Natural (I) - 1);

         if Pose (I).Confidence < Min_Conf then
            Failed_Conf := True;
         elsif Pose (I).X < -1.500 or else Pose (I).X > 1.500 or else
               Pose (I).Y < -1.500 or else Pose (I).Y > 1.500 or else
               Pose (I).Z < -1.500 or else Pose (I).Z > 1.500
         then
            Failed_Bounds := True;
         else
            if not Failed_Bounds and then not Failed_Conf then
               Count := Count + 1;
            end if;
         end if;
      end loop;

      Valid_Joints := Count;

      if Failed_Conf then
         Result := Low_Confidence;
      elsif Failed_Bounds then
         Result := Out_Of_Bounds;
      else
         Result := Pose_Valid;
      end if;
   end Validate_Hand_Pose;

   procedure Smooth_Joint (
      Current_Pos  : in     Coord_Val;
      Target_Pos   : in     Coord_Val;
      Max_Delta    : in     Coord_Val;
      Filtered_Pos :    out Coord_Val
   ) is
      Diff : constant Diff_Val := Diff_Val (Target_Pos) - Diff_Val (Current_Pos);
   begin
      if Diff > Diff_Val (Max_Delta) then
         if Current_Pos <= Coord_Val'Last - Max_Delta then
            Filtered_Pos := Current_Pos + Max_Delta;
         else
            Filtered_Pos := Coord_Val'Last;
         end if;
      elsif Diff < -Diff_Val (Max_Delta) then
         if Current_Pos >= Coord_Val'First + Max_Delta then
            Filtered_Pos := Current_Pos - Max_Delta;
         else
            Filtered_Pos := Coord_Val'First;
         end if;
      else
         Filtered_Pos := Target_Pos;
      end if;
   end Smooth_Joint;

end Sign_Pose_Validator;
