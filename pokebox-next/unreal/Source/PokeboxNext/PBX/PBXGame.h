// Pokebox Next — save game + the game-instance subsystem that owns the player's progress.
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "PBXGame.generated.h"

/** chapter 1 ("A Licence to Remember") steps */
UENUM()
enum class EPBXStep : uint8
{
	WakeUp = 0,     // head outside (Mum gives the hint)
	MeetRho,        // Rho greets you outside the house
	GoLab,          // meet Dr. Vale at Pokébox Labs
	Starter,        // choose your partner card
	Capture,        // catch your first wild Echo in the tall grass
	RhoBattle,      // rival battle at the Route 1 gate
	Rest,           // rest your team at home
	Gate,           // licence signed: the landslide is cleared, Route 1 is open
	Done,           // chapter 1 complete (left Lumen Harbor) -> chapter 2: cross Route 1
	Route1Clear     // reached the Mistvale gate at the west end of Route 1
};

USTRUCT()
struct FPBXMon
{
	GENERATED_BODY()
	UPROPERTY() FName Card;
	UPROPERTY() int32 Lv = 1;
	UPROPERTY() int32 XP = 0;
	UPROPERTY() int32 HP = -1; // -1 = full
};

UCLASS()
class UPBXSaveGame : public USaveGame
{
	GENERATED_BODY()
public:
	UPROPERTY() int32 Version = 1;
	UPROPERTY() bool bMale = true;
	UPROPERTY() uint8 Step = 0;
	UPROPERTY() TArray<FPBXMon> Team;        // battle team (max 6), [0] = partner that walks with you
	UPROPERTY() TArray<FPBXMon> Box;         // everything else you caught
	UPROPERTY() TArray<FName> Seen;
	UPROPERTY() int32 Coins = 0;
	UPROPERTY() int32 Captures = 0;
	UPROPERTY() int32 Wins = 0;
	UPROPERTY() float PlayTime = 0.f;
	UPROPERTY() FVector Pos = FVector::ZeroVector;
	UPROPERTY() float Yaw = 0.f;
	UPROPERTY() bool bHasPos = false;
	UPROPERTY() FString SavedAt;
	// v2 (Route 1). Old saves load with these defaults.
	UPROPERTY() FString Map;                 // level the player is in ("" = L_Town)
	UPROPERTY() int32 Balls = 5;
	UPROPERTY() int32 Potions = 1;
	UPROPERTY() TArray<FName> Beaten;        // trainers you have beaten (they don't challenge you again)
	UPROPERTY() TArray<FName> Picked;        // items you have picked up
};

UCLASS()
class UPBXGameSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()
public:
	static constexpr const TCHAR* Slot = TEXT("PokeboxNext_Slot1");

	UPROPERTY() TObjectPtr<UPBXSaveGame> State;

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	void NewGame(bool bMale);
	bool HasSave() const;
	bool Save(const FVector& Pos, float Yaw);
	bool Load();

	EPBXStep Step() const { return State ? (EPBXStep)State->Step : EPBXStep::WakeUp; }
	void SetStep(EPBXStep S) { if (State) State->Step = (uint8)S; }
	bool HasPartner() const { return State && State->Team.Num() > 0; }
	void HealAll();
	/** adds a caught/received card: team if there is room, else the box. Returns true if it joined the team */
	bool AddMon(FName Card, int32 Lv);

	// ---- level travel (kept here: the subsystem survives OpenLevel, the director does not)
	FString PendingSpot;            // spot id to arrive at in the next level
	bool bPendingContinue = false;  // "Continue" picked on the title screen of another level: load the save there
	int32 AutoResume = -1;          // -pbxauto: the step the next level's director continues from
	bool bAutoFail = false; int32 AutoShots = 0;
	static constexpr int32 TeamMax = 6;
};
