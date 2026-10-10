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
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;
	void Stylize(FPoseContext& Output) const;
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
	bool IsActionPlaying() const { return Action != nullptr && ActionTarget > 0.f; }

	// game-thread state, copied to the proxy every frame
	FPBXAnimLayer State[FPBXAnimProxy::NumLayers];
	/** body proportions (set by APBXCharacterBase::ApplyLook) */
	FPBXStyle Style;

protected:
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FPBXAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }

private:
	float ActionTarget = 0.f, ActionBlend = .2f, ActionTime = 0.f; bool bActionLoop = false;
	float FallW = 0.f;
};
