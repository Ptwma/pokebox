// Pokebox Next — the people (player, NPCs) and the paper Echoes.
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "PBXActors.generated.h"

class USkeletalMeshComponent;
class USpringArmComponent;
class UCameraComponent;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UTextRenderComponent;
class UPBXAnimInstance;

namespace PBXWorld
{
	/** ground height under a point (static world only), or Fallback if nothing is hit */
	float GroundZ(const UWorld* W, const FVector& P, float Up = 300.f, float Down = 1500.f, float Fallback = 0.f);
}

UCLASS()
class APBXCharacterBase : public ACharacter
{
	GENERATED_BODY()
public:
	APBXCharacterBase();
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Eyes;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Brows;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Hair;
	/** 3D garments (tools/clothes.py), skinned to the same bone names, driven through the leader pose */
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Clothes;

	/** Body: "m" / "f" = Quaternius base bodies (+ hair, painted body, 3D clothes), "boy" = Fab "Free Stylized Boy" (dressed already) */
	void ApplyLook(const FString& Body, const FString& HairName, float Scale = 1.f, const FString& Outfit = FString(), FLinearColor HairColor = FLinearColor(0, 0, 0, 0));
	UPBXAnimInstance* Anim() const;
	void PlayAction(const FString& Short, bool bLoop, float Blend = .2f);
	void StopAction(float Blend = .25f);
	void SetIdleAnim(const FString& Short);
	/** turn (smoothly) to look at a point */
	void FaceTowards(const FVector& P, bool bInstant = false);
	virtual void Tick(float Dt) override;
	bool bMaleLook = true;
protected:
	float TurnYaw = 0.f; bool bTurning = false;
};

UCLASS()
class APBXPlayer : public APBXCharacterBase
{
	GENERATED_BODY()
public:
	APBXPlayer();
	UPROPERTY(VisibleAnywhere) TObjectPtr<USpringArmComponent> Boom;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
	void SetRunning(bool bRun);
	void Zoom(float D);
	/** after a teleport: no camera lag for a couple of frames, so the camera doesn't trail from the old place (through walls / underground) */
	void SnapCamera();
	virtual void Tick(float Dt) override;
	bool bRunning = false;
	int32 SnapFrames = 0;
};

UCLASS()
class APBXNPC : public APBXCharacterBase
{
	GENERATED_BODY()
public:
	APBXNPC();
	UPROPERTY(VisibleAnywhere) TObjectPtr<UTextRenderComponent> Marker; // "!" when the story wants you to talk to them
	FName Id; FString DisplayName; FString IdleAnim;
	FVector Home; float HomeYaw = 0.f;
	void SetMarker(bool bOn);
	void ReturnToIdle();
	virtual void Tick(float Dt) override;
	// simple scripted walk (no navmesh needed): straight line to a goal, then a callback
	void WalkTo(const FVector& Goal, TFunction<void()> Done);
private:
	bool bWalking = false; FVector WalkGoal; TFunction<void()> WalkDone; float WalkT = 0.f;
};

/** a card's Echo: the die-cut art as a paper figure that hops around, follows you, and fights */
UCLASS()
class APBXEcho : public AActor
{
	GENERATED_BODY()
public:
	APBXEcho();
	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Pivot;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Paper;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MID;

	enum class EMode : uint8 { Idle, Follow, Wander, Stage };
	EMode Mode = EMode::Idle;
	FName CardId; float HeightCm = 100.f;
	TWeakObjectPtr<AActor> FollowTarget;
	FBox2D WanderBox = FBox2D(ForceInit); FVector Goal = FVector::ZeroVector; float Speed = 0.f;
	bool bFaint = false; bool bWild = false;

	bool Setup(FName Card, float Height);
	void Flash(const FLinearColor& C, float Strength = 3.f);
	void Lunge(const FVector& Dir, float Dist = 120.f);
	void Hurt();
	void SetFaint(bool b);
	void PopIn();
	void PlaceAt(const FVector& P);
	virtual void Tick(float Dt) override;
private:
	float T = 0.f, HopT = 0.f, FlashT = 0.f, LungeT = -1.f, HurtT = -1.f, PopT = 1.f, FaintK = 0.f, WanderWait = 0.f;
	FVector LungeDir = FVector::ZeroVector; float LungeDist = 0.f;
	FLinearColor FlashCol = FLinearColor::White; float FlashStrength = 0.f;
	float CurYaw = 0.f;
};
