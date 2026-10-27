pragma SPARK_Mode (On);

package Solar_Forge_Mint_Matrix is

   type Solar_Stability_Permille is range 0 .. 1000;
   Min_Stable_Harvesting : constant Solar_Stability_Permille := 990; -- 99.0% threshold
   Grams_Per_Kingscoin   : constant := 12;

   type Gros_Count_Type is range 0 .. 1_000_000;
   type Grams_Ag_Type is range 0 .. 12_000_000;
   type Axis_Score_Type is range 0 .. 100;

   type Matrix_Axis is (Axis_Power, Axis_Collateral, Axis_Cadence, Axis_Reserve);
   type Matrix_Array is array (Matrix_Axis) of Axis_Score_Type;

   type Forge_State is record
      Harvesting_Efficiency : Solar_Stability_Permille;
      Sun_Protocol_Active   : Boolean;
      Custody_Ag_Grams      : Grams_Ag_Type;
      Minted_Kingscoin      : Gros_Count_Type;
      Balancing_Matrix      : Matrix_Array;
      Forge_Online          : Boolean;
   end record;

   procedure Initialize_Forge
     (Forge      : out Forge_State;
      Initial_Ag : in  Grams_Ag_Type)
   with
     Global => null,
     Depends => (Forge => Initial_Ag),
     Post =>
       Forge.Forge_Online and then
       not Forge.Sun_Protocol_Active and then
       Forge.Harvesting_Efficiency = 0 and then
       Forge.Minted_Kingscoin = 0 and then
       Forge.Custody_Ag_Grams = Initial_Ag and then
       (for all A in Matrix_Axis => Forge.Balancing_Matrix (A) = 0);

   procedure Calibrate_Solar_Harvest
     (Forge     : in out Forge_State;
      Stability : in     Solar_Stability_Permille)
   with
     Global => null,
     Depends => (Forge =>+ Stability),
     Pre => Forge.Forge_Online,
     Post =>
       Forge.Harvesting_Efficiency = Stability and then
       Forge.Sun_Protocol_Active = (Stability >= Min_Stable_Harvesting) and then
       Forge.Forge_Online = Forge'Old.Forge_Online and then
       Forge.Custody_Ag_Grams = Forge'Old.Custody_Ag_Grams and then
       Forge.Minted_Kingscoin = Forge'Old.Minted_Kingscoin and then
       Forge.Balancing_Matrix = Forge'Old.Balancing_Matrix;

   procedure Update_Balancing_Matrix
     (Forge : in out Forge_State;
      Axis  : in     Matrix_Axis;
      Score : in     Axis_Score_Type)
   with
     Global => null,
     Depends => (Forge =>+ (Axis, Score)),
     Pre => Forge.Forge_Online,
     Post =>
       Forge.Balancing_Matrix (Axis) = Score and then
       (for all A in Matrix_Axis =>
          (if A /= Axis then Forge.Balancing_Matrix (A) = Forge'Old.Balancing_Matrix (A))) and then
       Forge.Forge_Online = Forge'Old.Forge_Online and then
       Forge.Harvesting_Efficiency = Forge'Old.Harvesting_Efficiency and then
       Forge.Sun_Protocol_Active = Forge'Old.Sun_Protocol_Active and then
       Forge.Custody_Ag_Grams = Forge'Old.Custody_Ag_Grams and then
       Forge.Minted_Kingscoin = Forge'Old.Minted_Kingscoin;

   procedure Mint_Solar_Kingscoin
     (Forge   : in out Forge_State;
      Amount  : in     Gros_Count_Type;
      Success : out    Boolean)
   with
     Global => null,
     Depends =>
       (Forge   =>+ Amount,
        Success => (Forge, Amount)),
     Pre => Forge.Forge_Online,
     Post =>
       (if Success then
          Forge.Minted_Kingscoin = Forge'Old.Minted_Kingscoin + Amount and then
          Grams_Ag_Type (Forge.Minted_Kingscoin) * Grams_Per_Kingscoin <= Forge.Custody_Ag_Grams and then
          Forge.Sun_Protocol_Active and then
          Forge.Harvesting_Efficiency >= Min_Stable_Harvesting
        else
          Forge.Minted_Kingscoin = Forge'Old.Minted_Kingscoin) and then
       Forge.Forge_Online = Forge'Old.Forge_Online and then
       Forge.Harvesting_Efficiency = Forge'Old.Harvesting_Efficiency and then
       Forge.Sun_Protocol_Active = Forge'Old.Sun_Protocol_Active and then
       Forge.Custody_Ag_Grams = Forge'Old.Custody_Ag_Grams and then
       Forge.Balancing_Matrix = Forge'Old.Balancing_Matrix;

end Solar_Forge_Mint_Matrix;
