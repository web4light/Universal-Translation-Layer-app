pragma SPARK_Mode (On);

package body Solar_Forge_Mint_Matrix is

   procedure Initialize_Forge
     (Forge      : out Forge_State;
      Initial_Ag : in  Grams_Ag_Type)
   is
   begin
      Forge.Harvesting_Efficiency := 0;
      Forge.Sun_Protocol_Active   := False;
      Forge.Custody_Ag_Grams      := Initial_Ag;
      Forge.Minted_Kingscoin      := 0;
      Forge.Balancing_Matrix      := (others => 0);
      Forge.Forge_Online          := True;
   end Initialize_Forge;

   procedure Calibrate_Solar_Harvest
     (Forge     : in out Forge_State;
      Stability : in     Solar_Stability_Permille)
   is
   begin
      Forge.Harvesting_Efficiency := Stability;
      Forge.Sun_Protocol_Active   := (Stability >= Min_Stable_Harvesting);
   end Calibrate_Solar_Harvest;

   procedure Update_Balancing_Matrix
     (Forge : in out Forge_State;
      Axis  : in     Matrix_Axis;
      Score : in     Axis_Score_Type)
   is
   begin
      Forge.Balancing_Matrix (Axis) := Score;
   end Update_Balancing_Matrix;

   procedure Mint_Solar_Kingscoin
     (Forge   : in out Forge_State;
      Amount  : in     Gros_Count_Type;
      Success : out    Boolean)
   is
      Matrix_Balanced : Boolean;
      Available_Coins : Gros_Count_Type;
   begin
      Matrix_Balanced :=
        Forge.Balancing_Matrix (Axis_Power) >= 80 and then
        Forge.Balancing_Matrix (Axis_Collateral) >= 80 and then
        Forge.Balancing_Matrix (Axis_Cadence) >= 80 and then
        Forge.Balancing_Matrix (Axis_Reserve) >= 80;

      Available_Coins := Gros_Count_Type (Forge.Custody_Ag_Grams / Grams_Per_Kingscoin);

      if Forge.Sun_Protocol_Active and then
         Forge.Harvesting_Efficiency >= Min_Stable_Harvesting and then
         Matrix_Balanced and then
         Amount > 0 and then
         Forge.Minted_Kingscoin <= Available_Coins and then
         Amount <= Available_Coins - Forge.Minted_Kingscoin
      then
         Forge.Minted_Kingscoin := Forge.Minted_Kingscoin + Amount;
         Success := True;
      else
         Success := False;
      end if;
   end Mint_Solar_Kingscoin;

end Solar_Forge_Mint_Matrix;
