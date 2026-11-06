// Pokebox Next — code-only animation for the Quaternius characters (no Animation Blueprint asset needed).
// A native AnimInstance whose proxy samples the Universal Animation Library sequences directly and blends them:
// idle / walk / jog / sprint by ground speed, a falling loop in the air, and one full-body "action" layer
// (talk, wave, interact, watering...) on top. UAL clips live on their own skeleton and are remapped by bone name.
#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "PBXAnim.generated.h"

class UAnimSequence;

namespace PBXAssets
{
	/** finds a UAL clip by its short name ("Idle_Loop", "Walk_Loop", ...) */
	UAnimSequence* Anim(const FString& Short);
	/** finds an asset of a class under a content folder whose name matches exactly (first hit) */
	UObject* FindByName(const FString& Folder, const FString& Name, UClass* Class);
}

/** cartoon proportions applied on top of the animation (component-space scale per body part) */
struct FPBXStyle
{
	float Head = 1.f, Hand = 1.f, Foot = 1.f;   // uniform
	float Limb = 1.f, Leg = 1.f, Chest = 1.f, Neck = 1.f;   // thickness across the bone
	bool bRelaxHands = false;   // MetaHuman bodies: the retargeted UAL finger tracks twist the fingers -> relaxed procedural hands
};

struct FPBXAnimLayer
{
	UAnimSequence* Seq = nullptr;
	float Time = 0.f, Weight = 0.f, Rate = 1.f;
	bool bLoop = true;
};

USTRUCT()
struct FPBXAnimProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()
	FPBXAnimProxy() {}
	FPBXAnimProxy(UAnimInstance* In) : FAnimInstanceProxy(In) {}
	static const int32 NumLayers = 6; // idle, walk, jog, sprint, fall, action
	FPBXAnimLayer L[NumLayers];
	FPBXStyle Style;
	FVector LookAt = FVector::ZeroVector, OwnerFwd = FVector(1, 0, 0); float LookW = 0.f; FTransform CompXf;
	void LookAtTarget(FPoseContext& Output) const;
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;
	void Stylize(FPoseContext& Output) const;
	void RelaxHands(FPoseContext& Output) const;
};

UCLASS(Transient, NotBlueprintable)
class UPBXAnimInstance : public UAnimInstance
{
	GENERATED_BODY()
public:
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Idle;
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Walk;
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Jog;
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Sprint;
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Fall;
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Action;

	/** plays a full-body clip over the locomotion (looped or once, then blends back) */
	void PlayAction(UAnimSequence* Seq, bool bLoop, float BlendIn = .2f);
	void StopAction(float BlendOut = .25f);
	void SetIdle(UAnimSequence* Seq) { if (Seq) Idle = Seq; }
	/** clip by short name for this character's skeleton ("_Boy" = retargeted set for the Fab boy) */
	UAnimSequence* Clip(const FString& Short) const;
	void SetSuffix(const FString& Suffix);
	FString AnimSuffix;
	bool IsActionPlaying() const { return Action != nullptr && ActionTarget > 0.f; }

	// game-thread state, copied to the proxy every frame
	FPBXAnimLayer State[FPBXAnimProxy::NumLayers];
	/** head/neck look-at (story conversations): world target, weight eased on the game thread */
	FVector LookTarget = FVector::ZeroVector, LookCur = FVector::ZeroVector; float LookWant = 0.f, LookW = 0.f;
	/** body proportions (set by APBXCharacterBase::ApplyLook) */
	FPBXStyle Style;
	/** body height / the height the clips were authored for: a 1.4 m kid takes shorter steps, so the same ground speed
	    needs a faster cycle (else the feet slide). Set by ApplyMetaHuman from the manifest height. */
	float StrideScale = 1.f;

protected:
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FPBXAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }

private:
	float ActionTarget = 0.f, ActionBlend = .2f, ActionTime = 0.f; bool bActionLoop = false;
	float FallW = 0.f;
	void LoadLocomotion();
};


// ------------------------------------------------------------------ faces (owner 2026-11-07: "exactly like Telltale")
// The MetaHuman face mesh: its joints copy the body (head, neck, jaw follow every gesture), and on top the control curves
// of the line being spoken (MetaHuman Animator audio-driven export, FA_<vo id>) feed the face's RigLogic post-process.
// Between lines the face blinks on its own.
USTRUCT()
struct FPBXFaceProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()
	FPBXFaceProxy() {}
	FPBXFaceProxy(UAnimInstance* In) : FAnimInstanceProxy(In) {}
	TArray<FTransform> BodyCS; TMap<FName, int32> BodyIdx;
	UAnimSequence* Seq = nullptr; float Time = 0.f, W = 0.f, Blink = 0.f;
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;
};

UCLASS(Transient, NotBlueprintable)
class UPBXFaceAnim : public UAnimInstance
{
	GENERATED_BODY()
public:
	TWeakObjectPtr<USkeletalMeshComponent> Body;
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Seq;
	float Time = 0.f, W = 0.f, WantW = 0.f, BlinkT = 2.f, Blink = 0.f;
	/** speak a line: the face curves of FA_<id> (if exported); false = no face animation for that line */
	bool Speak(const FString& Id);
	void Silence() { WantW = 0.f; }
protected:
	virtual void NativeUpdateAnimation(float Dt) override;
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FPBXFaceProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }
};
