// Pokebox Next — runs the level: story (chapter 1), people, doors, wild Echoes, battles, menus, saving.
// Map data (spots, doors, NPCs, grass...) comes from Content/PBX/Data/<Map>.json, written by tools/blender_town.py.
// Start the game with -pbxauto to have it play itself through the whole chapter and take screenshots (test mode).
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "PBX/PBXCore.h"
#include "PBX/PBXUI.h"
#include "PBX/PBXGame.h"
#include "PBXDirector.generated.h"

class APBXPlayer; class APBXNPC; class APBXEcho; class ACameraActor; class AStaticMeshActor; class UInputAction; class UInputMappingContext;
class UPBXGameSubsystem; class SPBXHud; class UTexture2D;
struct FInputActionValue;
class FJsonObject;

struct FPBXSpot { FVector Pos = FVector::ZeroVector; float Yaw = 0.f; };
struct FPBXDoor { FString Id, Label; bool bLocked = false; FPBXSpot Outside, Inside; FVector OutDoor = FVector::ZeroVector, InDoor = FVector::ZeroVector; };
struct FPBXLine { FName Who; FString Text; };

UCLASS()
class APBXDirector : public AActor
{
	GENERATED_BODY()
public:
	APBXDirector();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;
	virtual void EndPlay(const EEndPlayReason::Type R) override;

	// ---- input (from the controller)
	void InMove(FVector2D V); void InLook(FVector2D V); void InJump(); void InConfirm(); void InBack(); void InPause();
	void InRun(bool b); void InZoom(float D); void InNav(int32 Dx, int32 Dy); void InNumber(int32 N);
	bool WantsCursor() const;

private:
	// ---- data
	TSharedPtr<FJsonObject> Data;
	FPBXSpot NewGameSpot; TArray<FPBXDoor> Doors; TMap<FString, FPBXSpot> Spots; TArray<FBox2D> Grass; TArray<FVector> WildSpawns;
	FVector GatePos = FVector::ZeroVector; float GateExitX = 0.f; FVector2D BoundsCenter = FVector2D::ZeroVector; float BoundsRadius = 9000.f, WaterZ = -110.f; FPBXSpot SafeSpot;
	FVector StarterTable = FVector::ZeroVector, BedPos = FVector::ZeroVector;
	struct FSign { FVector Pos; FString Text; }; TArray<FSign> Signs;
	bool LoadData();
	FPBXSpot ReadSpot(const TSharedPtr<FJsonObject>& O) const;

	// ---- world
	UPROPERTY() TObjectPtr<APBXPlayer> Player;
	UPROPERTY() TObjectPtr<APBXEcho> Partner;
	UPROPERTY() TMap<FName, TObjectPtr<APBXNPC>> NPCs;
	UPROPERTY() TArray<TObjectPtr<APBXEcho>> Wilds;
	UPROPERTY() TArray<TObjectPtr<AActor>> GateBarrier;
	UPROPERTY() TArray<TObjectPtr<AStaticMeshActor>> TableCards;
	UPROPERTY() TArray<TObjectPtr<UTexture2D>> CardTex;
	UPROPERTY() TObjectPtr<ACameraActor> Cam;
	UPROPERTY() TObjectPtr<UPBXGameSubsystem> Game;
	void SpawnWorld();
	void SpawnNPCs();
	void RefreshWorld();
	void SpawnPartner(bool bPop);
	void PlacePlayer(const FPBXSpot& S);
	void UpdateWilds(float Dt);
	bool Inside() const;
	FVector PlayerLoc() const;
	UTexture2D* CardTexture(FName Card);

	// ---- UI
	TSharedPtr<FPBXUIModel> UI; TSharedPtr<SPBXHud> Hud;
	void Toast(const FString& T);
	void Splash(const FString& Title, const FString& Sub, float Secs = 2.6f);
	void UpdateObjective();
	void UpdatePrompt();
	FString SpeakerName(FName Who) const;

	// ---- script queue (dialogue, waits, fades...) — while it runs the player can't walk
	TArray<TFunction<bool(float)>> Queue; bool bConfirm = false; float StepT = 0.f; int32 QueueGen = 0;
	void Q(TFunction<bool(float)> F) { Queue.Add(MoveTemp(F)); }
	void QDo(TFunction<void()> F);
	void QWait(float S);
	void QSay(const TArray<FPBXLine>& Lines);
	void QFade(float To, float Secs = .35f);
	bool Busy() const { return Queue.Num() > 0; }

	// ---- interactions
	enum class EKind : uint8 { None, NPC, Door, Bed, Table, Sign };
	EKind NearKind = EKind::None; int32 NearIndex = -1; FName NearNPC;
	void FindNearest();
	void Interact();
	void TalkTo(APBXNPC* N);
	void UseDoor(const FPBXDoor& D, bool bFromOutside);
	void Rest();
	void ChooseStarter();
	TArray<FPBXLine> LinesFor(FName Who) const;

	// ---- story
	EPBXStep Step() const;
	void SetStep(EPBXStep S);
	void StoryTick(float Dt);
	void CompleteChapter();
	FVector ObjectiveTarget(FString& OutLabel) const;
	FVector LastSafe = FVector::ZeroVector; float SafeT = 0.f; float WarnT = 0.f;

	// ---- battle
	struct FBattleCtx
	{
		bool bActive = false, bWild = false, bTrainer = false, bChoosing = false, bStory = false;
		FPBXBattle B; TWeakObjectPtr<APBXEcho> Foe; TWeakObjectPtr<APBXEcho> Mine; FVector A, Bp, D, Side; bool bOwnsFoe = false;
		FName Trainer; float CamS = 1.f; TArray<int32> MoveCodes; int32 FoeLv = 10; TArray<int32> PreHP[2]; int32 PreAct[2] = { 0, 0 };
		TWeakObjectPtr<AStaticMeshActor> Ball;
	} Bt;
	void StartWildBattle(APBXEcho* W);
	void StartTrainerBattle(FName Who);
	void SetupStage(const FVector& FoePos);
	void ShowMoves();
	void PickMove(int32 i);
	void PlayEvents(const TArray<FPBXEvent>& Ev);
	TArray<FPBXEvent> DoRound(EPBXMove M, int32 To);
	void TryCapture();
	void EndBattle(const FString& Result);
	void SyncPlates();
	void Floater(const FVector& W, const FString& T, const FLinearColor& C);
	void SaveTeamHP();

	// ---- menus
	enum class EMenu : uint8 { None, Title, Gender, Pause, Controls, Complete, Confirm };
	EMenu Menu = EMenu::None;
	void ShowMenu(EMenu M);
	void OpenChoice(const FString& Title, const FString& Sub, const TArray<FPBXOption>& Opts, bool bCards, TFunction<void(int32)> Pick);
	void CloseChoice();
	void StartNewGame(bool bMale);
	void ContinueGame();
	void SaveNow(bool bToast);
	void ToTitle();

	// ---- autoplay test (-pbxauto)
	bool bAuto = false; int32 AutoStep = 0; float AutoT = 0.f, AutoStepT = 0.f; int32 AutoShots = 0; bool bAutoFail = false;
	void AutoTick(float Dt);
	void Shot(const FString& Name);
	void AutoNext() { AutoStep++; AutoStepT = 0.f; }
	void TeleportPlayer(const FVector& P, float Yaw);
	float PlayTimeAcc = 0.f;
	bool bRunHeld = false;
};

UCLASS()
class APBXGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	APBXGameMode();
	virtual void BeginPlay() override;
};

UCLASS()
class APBXController : public APlayerController
{
	GENERATED_BODY()
public:
	TWeakObjectPtr<APBXDirector> Director;
protected:
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float Dt) override;
private:
	UPROPERTY() TObjectPtr<UInputMappingContext> IMC;
	UPROPERTY() TArray<TObjectPtr<UInputAction>> Actions;
	UInputAction* MakeAction(FName N, bool bAxis2D, bool bAxis1D = false);
};
