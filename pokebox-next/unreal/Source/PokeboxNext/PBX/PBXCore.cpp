#include "PBX/PBXCore.h"
#include "Misc/Paths.h"

// ------------------------------------------------------------------ cards
FString FPBXCardDef::EchoTexturePath() const
{
	const FString N = TEXT("T_Echo_") + Id.ToString();
	return FString::Printf(TEXT("/Game/PBX/Echo/%s.%s"), *N, *N);
}

FString FPBXCardDef::CardImagePath() const
{
	return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../pokemon-card-scraper/pokemon_cards/images") / (Id.ToString() + TEXT(".jpg")));
}

namespace PBXData
{
	const TArray<FPBXCardDef>& Cards()
	{
		static TArray<FPBXCardDef> C;
		if (C.Num() == 0)
		{
			auto Add = [](const TCHAR* Id, const TCHAR* Name, const TCHAR* Type, int32 HP, int32 Atk, int32 Spd, int32 R, float Size)
			{
				FPBXCardDef D; D.Id = Id; D.Name = Name; D.Type = Type; D.HP = HP; D.Atk = Atk; D.Spd = Spd; D.Rarity = R; D.Size = Size; C.Add(D);
			};
			// starters (Dr. Vale's three cards)
			Add(TEXT("Bulbasaur_MEW_001"), TEXT("Bulbasaur"), TEXT("Grass"), 130, 59, 84, 2, 1.0f);
			Add(TEXT("Charmander_MEW_004"), TEXT("Charmander"), TEXT("Fire"), 130, 60, 75, 3, 1.05f);
			Add(TEXT("Squirtle_PGO_015"), TEXT("Squirtle"), TEXT("Water"), 100, 45, 94, 1, 1.0f);
			// wild Echoes of the west road
			Add(TEXT("Pidgey_OBF_162"), TEXT("Pidgey"), TEXT("Colorless"), 100, 49, 48, 0, .85f);
			Add(TEXT("Lechonk_PAF_071"), TEXT("Lechonk"), TEXT("Colorless"), 100, 50, 78, 0, .85f);
			Add(TEXT("Starly_SVI_148"), TEXT("Starly"), TEXT("Colorless"), 100, 51, 72, 0, .8f);
			Add(TEXT("Jigglypuff_MEW_039"), TEXT("Jigglypuff"), TEXT("Colorless"), 90, 35, 43, 0, .8f);
			Add(TEXT("Spearow_MEW_021"), TEXT("Spearow"), TEXT("Colorless"), 100, 36, 90, 0, .85f);
			// Rho's partner
			Add(TEXT("Eevee_MEW_133"), TEXT("Eevee"), TEXT("Colorless"), 110, 46, 70, 0, .9f);
		}
		return C;
	}
	const FPBXCardDef* Card(FName Id) { return Cards().FindByPredicate([&](const FPBXCardDef& D) { return D.Id == Id; }); }
	TArray<FName> Starters() { return { TEXT("Bulbasaur_MEW_001"), TEXT("Charmander_MEW_004"), TEXT("Squirtle_PGO_015") }; }
	TArray<FName> WildPool() { return { TEXT("Pidgey_OBF_162"), TEXT("Lechonk_PAF_071"), TEXT("Starly_SVI_148"), TEXT("Jigglypuff_MEW_039"), TEXT("Spearow_MEW_021") }; }
	FName RivalCard() { return TEXT("Eevee_MEW_133"); }
	FLinearColor TypeColor(const FString& T)
	{
		static const TMap<FString, FColor> M = { {TEXT("Grass"), FColor(0x5f, 0xae, 0x4f)}, {TEXT("Fire"), FColor(0xe8, 0x60, 0x3c)}, {TEXT("Water"), FColor(0x3d, 0x8f, 0xd6)},
			{TEXT("Lightning"), FColor(0xf2, 0xc2, 0x30)}, {TEXT("Psychic"), FColor(0xb0, 0x5f, 0xc9)}, {TEXT("Fighting"), FColor(0xb5, 0x67, 0x3a)}, {TEXT("Darkness"), FColor(0x3f, 0x4a, 0x5a)},
			{TEXT("Metal"), FColor(0x8e, 0x9a, 0xa6)}, {TEXT("Dragon"), FColor(0xc2, 0x9a, 0x2c)}, {TEXT("Colorless"), FColor(0xc9, 0xc2, 0xb0)} };
		const FColor* C = M.Find(T); return FLinearColor(C ? *C : FColor(200, 200, 200));
	}
	float LvMult(int32 Lv) { return .72f + Lv * .0125f; }
	int32 StartLevel(const FPBXCardDef& C) { return 12 + C.Rarity * 2; }
}

// ------------------------------------------------------------------ fighters
FPBXFighter FPBXFighter::Make(const FPBXCardDef& C, int32 Lv, float L)
{
	FPBXFighter F; F.CardId = C.Id; F.Name = C.Name; F.Type = C.Type; F.Lv = Lv;
	F.MaxHP = F.HP = FMath::RoundToInt(C.HP * L); F.Atk = FMath::RoundToInt(C.Atk * L);
	F.Def = FMath::RoundToInt(C.HP * .25f + C.Atk * .2f); F.Spd = C.Spd;
	return F;
}

// ------------------------------------------------------------------ rules
float FPBXBattle::Mult(const FString& A, const FString& D)
{
	static const TMap<FString, TArray<FString>> Weak = {
		{TEXT("Fire"), {TEXT("Grass"), TEXT("Metal")}}, {TEXT("Water"), {TEXT("Fire")}}, {TEXT("Grass"), {TEXT("Water"), TEXT("Fighting")}},
		{TEXT("Lightning"), {TEXT("Water"), TEXT("Colorless")}}, {TEXT("Fighting"), {TEXT("Lightning"), TEXT("Darkness"), TEXT("Colorless"), TEXT("Metal")}},
		{TEXT("Psychic"), {TEXT("Fighting")}}, {TEXT("Darkness"), {TEXT("Psychic")}}, {TEXT("Metal"), {TEXT("Psychic"), TEXT("Fairy")}}, {TEXT("Dragon"), {TEXT("Dragon")}} };
	static const TMap<FString, TArray<FString>> Resist = {
		{TEXT("Fire"), {TEXT("Grass")}}, {TEXT("Water"), {TEXT("Fire"), TEXT("Metal")}}, {TEXT("Grass"), {TEXT("Water"), TEXT("Lightning")}},
		{TEXT("Lightning"), {TEXT("Metal")}}, {TEXT("Metal"), {TEXT("Grass")}}, {TEXT("Darkness"), {TEXT("Psychic")}} };
	float M = 1.f;
	if (const TArray<FString>* W = Weak.Find(A)) if (W->Contains(D)) M *= 1.5f;
	if (const TArray<FString>* R = Resist.Find(D)) if (R->Contains(A)) M *= .75f;
	return M;
}

const FPBXSig& FPBXBattle::SigOf(const FString& T)
{
	static const TMap<FString, FPBXSig> S = {
		{TEXT("Fire"), {TEXT("Flame Burst"), TEXT("burn"), TEXT("burns for 3 turns")}}, {TEXT("Water"), {TEXT("Hydro Cannon"), TEXT("soak"), TEXT("lowers their speed")}},
		{TEXT("Grass"), {TEXT("Leaf Drain"), TEXT("drain"), TEXT("heals 35% of damage")}}, {TEXT("Lightning"), {TEXT("Thunder Shock"), TEXT("para"), TEXT("30% paralysis")}},
		{TEXT("Psychic"), {TEXT("Mind Crush"), TEXT("weaken"), TEXT("lowers their attack")}}, {TEXT("Fighting"), {TEXT("Close Combat"), TEXT("pierce"), TEXT("ignores guard")}},
		{TEXT("Darkness"), {TEXT("Night Slash"), TEXT("crit"), TEXT("high critical chance")}}, {TEXT("Metal"), {TEXT("Iron Bash"), TEXT("shield"), TEXT("raises your defense")}},
		{TEXT("Dragon"), {TEXT("Dragon Rush"), TEXT("none"), TEXT("massive power")}}, {TEXT("Colorless"), {TEXT("Hyper Strike"), TEXT("none"), TEXT("reliable damage")}} };
	const FPBXSig* F = S.Find(T); return F ? *F : S[TEXT("Colorless")];
}

int32 FPBXBattle::Power(EPBXMove M) { return M == EPBXMove::Attack ? 30 : M == EPBXMove::Sig ? 58 : M == EPBXMove::Ult ? 92 : 0; }
int32 FPBXBattle::Cost(EPBXMove M) { return M == EPBXMove::Sig ? 2 : M == EPBXMove::Ult ? 4 : 0; }
int32 FPBXBattle::Gain(EPBXMove M) { return (M == EPBXMove::Attack || M == EPBXMove::Guard) ? 1 : 0; }

int32 FPBXBattle::Estimate(const FPBXFighter& A, const FPBXFighter& D, EPBXMove M) const
{
	const int32 P = Power(M); if (!P) return 0;
	return FMath::RoundToInt(P * (A.Atk * A.BuffAtk) / (D.Def * D.BuffDef + 40.f) * 1.22f * Mult(A.Type, D.Type));
}

FPBXEvent FPBXBattle::Damage(FPBXFighter& Att, FPBXFighter& Def, EPBXMove M)
{
	const FPBXSig* Sig = M == EPBXMove::Sig ? &SigOf(Att.Type) : nullptr;
	const float Type = Mult(Att.Type, Def.Type), Roll = .9f + FMath::FRand() * .15f;
	const float CritP = (Sig && Sig->Fx == TEXT("crit")) ? .3f : .06f; const float Crit = FMath::FRand() < CritP ? 1.5f : 1.f;
	float D = Power(M) * (Att.Atk * Att.BuffAtk) / (Def.Def * Def.BuffDef + 40.f) * 1.22f * Type * Roll * Crit;
	const bool Pierce = Sig && Sig->Fx == TEXT("pierce");
	if (Def.bGuard && !Pierce) D *= .45f;
	FPBXEvent E; E.Kind = FPBXEvent::Hit; E.Dmg = FMath::Max(3, FMath::RoundToInt(D)); E.bEff = Type > 1.f; E.bWeak = Type < 1.f; E.bCrit = Crit > 1.f; E.bGuarded = Def.bGuard && !Pierce;
	return E;
}

FPBXBattle::FAct FPBXBattle::AiAction()
{
	FPBXFighter& Me = Active(1); const FPBXFighter& Foe = Active(0);
	TArray<int32> Bench; for (int32 i = 0; i < Team[1].Num(); i++) if (i != Act[1] && Team[1][i].HP > 0) Bench.Add(i);
	if (Mult(Foe.Type, Me.Type) > 1.f && Me.HP < Me.MaxHP * .5f && Bench.Num() && FMath::FRand() < .45f)
	{
		int32 Good = Bench[0]; for (int32 i : Bench) if (Mult(Foe.Type, Team[1][i].Type) <= 1.f) { Good = i; break; }
		return { EPBXMove::Switch, Good };
	}
	if (CanUse(Me, EPBXMove::Ult) && (FMath::FRand() < .7f || Foe.HP < Estimate(Me, Foe, EPBXMove::Ult))) return { EPBXMove::Ult, -1 };
	if (CanUse(Me, EPBXMove::Sig) && (Foe.HP <= Estimate(Me, Foe, EPBXMove::Sig) || FMath::FRand() < .35f)) return { EPBXMove::Sig, -1 };
	if (Me.HP < Me.MaxHP * .35f && !Me.bGuard && FMath::FRand() < .3f) return { EPBXMove::Guard, -1 };
	return { EPBXMove::Attack, -1 };
}

TArray<FPBXEvent> FPBXBattle::Round(EPBXMove PlayerMove, int32 SwitchTo)
{
	TArray<FPBXEvent> Ev; FAct Acts[2]; Acts[0] = { PlayerMove, SwitchTo }; Acts[1] = AiAction();
	for (int32 S = 0; S < 2; S++) if (Acts[S].Kind == EPBXMove::Switch && Acts[S].To >= 0)
	{
		Active(S).bGuard = false; Act[S] = Acts[S].To; FPBXEvent E; E.Kind = FPBXEvent::Switch; E.Side = S; E.To = Acts[S].To; Ev.Add(E);
	}
	for (int32 S = 0; S < 2; S++) Active(S).bGuard = false;
	for (int32 S = 0; S < 2; S++) if (Acts[S].Kind == EPBXMove::Guard)
	{
		FPBXFighter& F = Active(S); F.bGuard = true; F.Energy = FMath::Min(EnergyMax, F.Energy + 1); FPBXEvent E; E.Kind = FPBXEvent::Guard; E.Side = S; Ev.Add(E);
	}
	auto Spd = [&](int32 S) { return Active(S).Spd * Active(S).BuffSpd; };
	int32 Order[2] = { 0, 1 };
	if (Spd(1) > Spd(0) || (Spd(1) == Spd(0) && FMath::RandBool())) { Order[0] = 1; Order[1] = 0; }
	bool Skip[2] = { false, false };
	for (int32 k = 0; k < 2; k++)
	{
		const int32 S = Order[k];
		if (!Over.IsEmpty()) break;
		if (Skip[S]) continue;
		FAct& A = Acts[S]; FPBXFighter& Me = Active(S); const int32 O = 1 - S; FPBXFighter& Foe = Active(O);
		if (Me.HP <= 0 || Power(A.Kind) == 0) continue;
		if (!CanUse(Me, A.Kind)) A.Kind = EPBXMove::Attack;
		if (Me.Status == TEXT("para") && FMath::FRand() < .3f) { FPBXEvent E; E.Kind = FPBXEvent::Para; E.Side = S; Ev.Add(E); continue; }
		Me.Energy = FMath::Clamp(Me.Energy - Cost(A.Kind) + Gain(A.Kind), 0, EnergyMax);
		FPBXEvent R = Damage(Me, Foe, A.Kind);
		Foe.HP = FMath::Max(Foe.MinHP, Foe.HP - R.Dmg);
		const FPBXSig* Sig = A.Kind == EPBXMove::Sig ? &SigOf(Me.Type) : nullptr;
		R.Side = S; R.MoveKind = A.Kind; R.Type = Me.Type;
		R.Move = A.Kind == EPBXMove::Attack ? TEXT("Attack") : A.Kind == EPBXMove::Ult ? TEXT("Ultimate") : Sig->Name;
		Ev.Add(R);
		if (Sig && Foe.HP > 0)
		{
			FPBXEvent E; E.Side = O;
			if (Sig->Fx == TEXT("burn") && Foe.Status.IsNone()) { Foe.Status = TEXT("burn"); Foe.StatusT = 3; E.Kind = FPBXEvent::Status; E.St = Foe.Status; Ev.Add(E); }
			else if (Sig->Fx == TEXT("para") && Foe.Status.IsNone() && FMath::FRand() < .3f) { Foe.Status = TEXT("para"); Foe.StatusT = 2; E.Kind = FPBXEvent::Status; E.St = Foe.Status; Ev.Add(E); }
			else if (Sig->Fx == TEXT("soak")) { Foe.BuffSpd = FMath::Max(.6f, Foe.BuffSpd - .2f); E.Kind = FPBXEvent::Debuff; E.Stat = TEXT("SPD"); Ev.Add(E); }
			else if (Sig->Fx == TEXT("weaken")) { Foe.BuffAtk = FMath::Max(.6f, Foe.BuffAtk - .15f); E.Kind = FPBXEvent::Debuff; E.Stat = TEXT("ATK"); Ev.Add(E); }
		}
		if (Sig && Sig->Fx == TEXT("drain")) { const int32 H = FMath::RoundToInt(R.Dmg * .35f); Me.HP = FMath::Min(Me.MaxHP, Me.HP + H); FPBXEvent E; E.Kind = FPBXEvent::Heal; E.Side = S; E.Dmg = H; Ev.Add(E); }
		if (Sig && Sig->Fx == TEXT("shield")) { Me.BuffDef = FMath::Min(1.6f, Me.BuffDef + .2f); FPBXEvent E; E.Kind = FPBXEvent::Buff; E.Side = S; E.Stat = TEXT("DEF"); Ev.Add(E); }
		if (KO(O, S, Ev, Skip)) break;
	}
	for (int32 S = 0; S < 2; S++)
	{
		if (!Over.IsEmpty()) break;
		FPBXFighter& F = Active(S); if (F.HP <= 0 || F.Status.IsNone()) continue;
		if (F.Status == TEXT("burn"))
		{
			const int32 D = FMath::Max(4, FMath::RoundToInt(F.MaxHP * .06f)); F.HP = FMath::Max(F.MinHP, F.HP - D);
			FPBXEvent E; E.Kind = FPBXEvent::Burn; E.Side = S; E.Dmg = D; Ev.Add(E);
			if (KO(S, 1 - S, Ev, Skip)) break;
		}
		if (--F.StatusT <= 0) { FPBXEvent E; E.Kind = FPBXEvent::Cure; E.Side = S; E.St = F.Status; Ev.Add(E); F.Status = NAME_None; }
	}
	Turn++;
	return Ev;
}

bool FPBXBattle::KO(int32 O, int32 Winner, TArray<FPBXEvent>& Ev, bool Skip[2])
{
	if (Active(O).HP > 0) return false;
	{ FPBXEvent E; E.Kind = FPBXEvent::KO; E.Side = O; Ev.Add(E); }
	int32 Next = -1; for (int32 i = 0; i < Team[O].Num(); i++) if (Team[O][i].HP > 0) { Next = i; break; }
	if (Next < 0) { Over = Winner == 0 ? TEXT("win") : TEXT("lose"); FPBXEvent E; E.Kind = FPBXEvent::End; E.Result = Over; Ev.Add(E); return true; }
	Act[O] = Next; Skip[O] = true; FPBXEvent E; E.Kind = FPBXEvent::Switch; E.Side = O; E.To = Next; E.bForced = true; Ev.Add(E);
	return false;
}

float FPBXBattle::CaptureChance() const
{
	const FPBXFighter& F = Active(1); const FPBXCardDef* C = PBXData::Card(F.CardId);
	return FMath::Clamp(.22f + (1.f - float(F.HP) / F.MaxHP) * .72f - (C ? C->Rarity : 0) * .05f + (F.Status.IsNone() ? 0.f : .1f), .08f, .95f);
}
