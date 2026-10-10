// Pokebox Next — data (cards, types) and the battle rules, ported 1:1 from pokebox-game/js/battle.js.
//   damage = power × ATK / (DEF + 40) × 1.22 × type × random(0.9–1.05) × crit(1.5, 6%)
#pragma once
#include "CoreMinimal.h"

/** one card the game knows about. Card art never ships in git: Echo cut-outs are imported from the user's PC. */
struct FPBXCardDef
{
	FName Id;          // e.g. "Bulbasaur_MEW_001" (also the card image file stem)
	FString Name;
	FString Type;      // Grass, Fire, Water, Lightning, Psychic, Fighting, Darkness, Metal, Dragon, Colorless
	int32 HP = 100, Atk = 40, Spd = 50, Rarity = 0;
	float Size = 1.0f; // Echo standee height multiplier
	FString EchoTexturePath() const;
	FString CardImagePath() const; // absolute path of the card scan on the PC (for the starter cards / UI)
};

namespace PBXData
{
	const TArray<FPBXCardDef>& Cards();
	const FPBXCardDef* Card(FName Id);
	TArray<FName> Starters();
	TArray<FName> WildPool();
	FName RivalCard();
	FLinearColor TypeColor(const FString& Type);
	float LvMult(int32 Lv);
	int32 StartLevel(const FPBXCardDef& C);
}

struct FPBXFighter
{
	FName CardId; FString Name; FString Type;
	int32 MaxHP = 1, HP = 1, Atk = 1, Def = 1, Spd = 1, Lv = 1;
	int32 Energy = 0; bool bGuard = false;
	FName Status; int32 StatusT = 0;
	float BuffAtk = 1, BuffDef = 1, BuffSpd = 1;
	int32 MinHP = 0;  // story captures can't knock the Echo out
	static FPBXFighter Make(const FPBXCardDef& C, int32 Lv, float LvlMult);
};

enum class EPBXMove : uint8 { Attack, Sig, Ult, Guard, Switch };

struct FPBXSig { FString Name; FString Fx; FString Note; };

struct FPBXEvent
{
	enum EKind : uint8 { Hit, Guard, Switch, Para, Status, Debuff, Heal, Buff, Burn, Cure, KO, End };
	EKind Kind = Hit; int32 Side = 0; // 0 = player, 1 = enemy
	FString Move, Type, Stat, Result; FName St;
	int32 Dmg = 0, To = 0; bool bEff = false, bWeak = false, bCrit = false, bGuarded = false, bForced = false;
	EPBXMove MoveKind = EPBXMove::Attack;
};

class FPBXBattle
{
public:
	TArray<FPBXFighter> Team[2];
	int32 Act[2] = { 0, 0 };
	int32 Turn = 1;
	FString Over; // "", "win", "lose"

	static const int32 EnergyMax = 5;
	static float Mult(const FString& Att, const FString& Def);
	static const FPBXSig& SigOf(const FString& Type);
	static int32 Power(EPBXMove M);
	static int32 Cost(EPBXMove M);
	static int32 Gain(EPBXMove M);

	FPBXFighter& Active(int32 S) { return Team[S][Act[S]]; }
	const FPBXFighter& Active(int32 S) const { return Team[S][Act[S]]; }
	bool CanUse(const FPBXFighter& F, EPBXMove M) const { return F.Energy >= Cost(M); }
	int32 Estimate(const FPBXFighter& A, const FPBXFighter& D, EPBXMove M) const;
	TArray<FPBXEvent> Round(EPBXMove PlayerMove, int32 SwitchTo = -1);
	float CaptureChance() const;

private:
	struct FAct { EPBXMove Kind = EPBXMove::Attack; int32 To = -1; };
	FAct AiAction();
	FPBXEvent Damage(FPBXFighter& Att, FPBXFighter& Def, EPBXMove M);
	bool KO(int32 O, int32 Winner, TArray<FPBXEvent>& Ev, bool Skip[2]);
};
