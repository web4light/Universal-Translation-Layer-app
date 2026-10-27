pragma SPARK_Mode (On);

package Sign_Pose_Validator is

   -- Pevná řádová čárka pro 3D prostor posunkového jazyka (Three.js koordináty)
   type Coord_Val is delta 0.001 range -2.000 .. 2.000;
   for Coord_Val'Small use 0.001;

   type Diff_Val is delta 0.001 range -5.000 .. 5.000;
   for Diff_Val'Small use 0.001;

   type Confidence_Val is delta 0.01 range 0.00 .. 1.00;
   for Confidence_Val'Small use 0.01;

   type Joint_Index is range 1 .. 21; -- 21 kloubů lidské ruky (MediaPipe / WebXR)

   type Joint_Point is record
      X          : Coord_Val;
      Y          : Coord_Val;
      Z          : Coord_Val;
      Confidence : Confidence_Val;
   end record;

   type Hand_Skeleton is array (Joint_Index) of Joint_Point;

   type Validation_Result is (Pose_Valid, Out_Of_Bounds, Low_Confidence, Kinematic_Anomaly);

   -- Validace anatomické integrity a limitů posunku ruky
   procedure Validate_Hand_Pose (
      Pose         : in  Hand_Skeleton;
      Min_Conf     : in  Confidence_Val;
      Result       : out Validation_Result;
      Valid_Joints : out Natural
   )
   with
      Global  => null,
      Depends => (
         Result       => (Pose, Min_Conf),
         Valid_Joints => (Pose, Min_Conf)
      ),
      Post    => Valid_Joints <= 21 and then
                 (if Result = Pose_Valid then Valid_Joints = 21 else True);

   -- Bezpečná filtrace jitteru / šumu v reálném čase
   procedure Smooth_Joint (
      Current_Pos  : in     Coord_Val;
      Target_Pos   : in     Coord_Val;
      Max_Delta    : in     Coord_Val;
      Filtered_Pos :    out Coord_Val
   )
   with
      Global  => null,
      Depends => (Filtered_Pos => (Current_Pos, Target_Pos, Max_Delta)),
      Pre     => Max_Delta >= 0.000,
      Post    => Filtered_Pos in Coord_Val'Range;

end Sign_Pose_Validator;
