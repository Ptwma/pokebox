#include "PBX/PBXAnim.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "AnimationRuntime.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

// ------------------------------------------------------------------ asset lookup
namespace PBXAssets
{
	static TArray<FAssetData> Scan(const FString& Folder)
	{
		TArray<FAssetData> Out;
		IAssetRegistry& AR = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
		static TSet<FString> Scanned;
		if (!Scanned.Contains(Folder)) { AR.ScanPathsSynchronous({ Folder }, false); Scanned.Add(Folder); }
		AR.GetAssetsByPath(FName(*Folder), Out, true);
		return Out;
	}

	UAnimSequence* Anim(const FString& Short)
	{
		static TMap<FString, FAssetData> Map;
		static TMap<FString, TObjectPtr<UAnimSequence>> Loaded;
		if (Map.Num() == 0)
		{
			for (const FAssetData& A : Scan(TEXT("/Game/PBX/Characters/Anim")))
			{
				if (A.AssetClassPath.GetAssetName() != FName(TEXT("AnimSequence"))) continue;
				FString N = A.AssetName.ToString();
				for (const TCHAR* P : { TEXT("UAL1_Standard"), TEXT("UAL2_Standard") }) if (N.StartsWith(P)) { N.RightChopInline(FCString::Strlen(P)); break; }
				Map.Add(N, A);
			}
		}
		if (TObjectPtr<UAnimSequence>* L = Loaded.Find(Short)) return *L;
		const FAssetData* A = Map.Find(Short); if (!A) { UE_LOG(LogTemp, Warning, TEXT("[PBX] anim not found: %s"), *Short); return nullptr; }
		UAnimSequence* S = Cast<UAnimSequence>(A->GetAsset());
		if (S) { S->AddToRoot(); Loaded.Add(Short, S); }
		return S;
	}

	UObject* FindByName(const FString& Folder, const FString& Name, UClass* Class)
	{
		for (const FAssetData& A : Scan(Folder))
			if (A.AssetName.ToString() == Name && (!Class || A.AssetClassPath == Class->GetClassPathName())) return A.GetAsset();
		return nullptr;
	}
}

// ------------------------------------------------------------------ game thread
void UPBXAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();
	if (!Idle) Idle = PBXAssets::Anim(TEXT("Idle_Loop"));
	if (!Walk) Walk = PBXAssets::Anim(TEXT("Walk_Loop"));
	if (!Jog) Jog = PBXAssets::Anim(TEXT("Jog_Fwd_Loop"));
	if (!Sprint) Sprint = PBXAssets::Anim(TEXT("Sprint_Loop"));
	if (!Fall) Fall = PBXAssets::Anim(TEXT("Jump_Loop"));
	for (int32 i = 0; i < FPBXAnimProxy::NumLayers; i++) State[i].Time = FMath::FRand() * 2.f;  // NPCs don't idle in sync
}

void UPBXAnimInstance::PlayAction(UAnimSequence* Seq, bool bLoop, float BlendIn)
{
	if (!Seq) return;
	if (Action != Seq || !bLoop) ActionTime = 0.f;
	Action = Seq; bActionLoop = bLoop; ActionTarget = 1.f; ActionBlend = FMath::Max(.05f, BlendIn);
}

void UPBXAnimInstance::StopAction(float BlendOut) { ActionTarget = 0.f; ActionBlend = FMath::Max(.05f, BlendOut); }

void UPBXAnimInstance::NativeUpdateAnimation(float Dt)
{
	Super::NativeUpdateAnimation(Dt);
	float Speed = 0.f; bool bFalling = false;
	if (const ACharacter* C = Cast<ACharacter>(TryGetPawnOwner()))
	{
		Speed = C->GetVelocity().Size2D();
		if (const UCharacterMovementComponent* M = C->GetCharacterMovement()) bFalling = M->IsFalling();
	}
	// locomotion targets
	float W[4] = { 0, 0, 0, 0 };
	if (Speed < 10.f) W[0] = 1.f;
	else if (Speed < 160.f) { const float k = Speed / 160.f; W[0] = 1.f - k; W[1] = k; }
	else if (Speed < 380.f) { const float k = (Speed - 160.f) / 220.f; W[1] = 1.f - k; W[2] = k; }
	else if (Speed < 620.f) { const float k = (Speed - 380.f) / 240.f; W[2] = 1.f - k; W[3] = k; }
	else W[3] = 1.f;
	const float Rates[4] = { 1.f, FMath::Clamp(Speed / 140.f, .7f, 1.4f), FMath::Clamp(Speed / 380.f, .75f, 1.35f), FMath::Clamp(Speed / 600.f, .8f, 1.3f) };
	FallW = FMath::FInterpTo(FallW, bFalling ? 1.f : 0.f, Dt, bFalling ? 8.f : 14.f);
	// action layer
	float& AW = State[5].Weight;
	if (Action && !bActionLoop)
	{
		const float Len = Action->GetPlayLength();
		if (ActionTime >= Len - ActionBlend) ActionTarget = 0.f;
	}
	AW = FMath::FInterpConstantTo(AW, ActionTarget, Dt, 1.f / ActionBlend);
	if (AW <= 0.f && ActionTarget <= 0.f) Action = nullptr;
	ActionTime += Dt;

	UAnimSequence* Seqs[5] = { Idle, Walk, Jog, Sprint, Fall };
	for (int32 i = 0; i < 4; i++)
	{
		FPBXAnimLayer& L = State[i];
		L.Seq = Seqs[i]; L.Rate = Rates[i]; L.bLoop = true;
		const float Target = W[i] * (1.f - FallW) * (1.f - AW);
		L.Weight = FMath::FInterpTo(L.Weight, Target, Dt, 12.f);
		if (L.Weight < .002f && Target <= 0.f) L.Weight = 0.f;
	}
	State[4].Seq = Fall; State[4].bLoop = true; State[4].Rate = 1.f; State[4].Weight = FallW * (1.f - AW);
	State[5].Seq = Action; State[5].bLoop = bActionLoop; State[5].Rate = 1.f;
	for (int32 i = 0; i < FPBXAnimProxy::NumLayers; i++)
	{
		FPBXAnimLayer& L = State[i];
		if (i == 5) { L.Time = ActionTime; }
		else L.Time += Dt * L.Rate;
		if (L.Seq)
		{
			const float Len = FMath::Max(.01f, L.Seq->GetPlayLength());
			L.Time = L.bLoop ? FMath::Fmod(L.Time, Len) : FMath::Min(L.Time, Len - .001f);
		}
	}
}

// ------------------------------------------------------------------ worker thread
void FPBXAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	if (const UPBXAnimInstance* I = Cast<UPBXAnimInstance>(InAnimInstance))
		for (int32 i = 0; i < NumLayers; i++) L[i] = I->State[i];
}

bool FPBXAnimProxy::Evaluate(FPoseContext& Output)
{
	float Total = 0.f; bool bAny = false;
	for (int32 i = 0; i < NumLayers; i++)
	{
		const FPBXAnimLayer& Ly = L[i];
		if (!Ly.Seq || Ly.Weight <= .001f) continue;
		FPoseContext P(Output);
		FAnimationPoseData PD(P);
		Ly.Seq->GetAnimationPose(PD, FAnimExtractContext((double)Ly.Time, false));
		if (!bAny)
		{
			Output.Pose = P.Pose; Output.Curve = P.Curve; Output.CustomAttributes = P.CustomAttributes;
			Total = Ly.Weight; bAny = true;
		}
		else
		{
			const float WOne = Total / (Total + Ly.Weight);
			FPoseContext Tmp(Output);
			FAnimationPoseData A(Output), Out(Tmp);
			FAnimationRuntime::BlendTwoPosesTogether(A, PD, WOne, Out);
			Output.Pose = Tmp.Pose; Output.Curve = Tmp.Curve; Output.CustomAttributes = Tmp.CustomAttributes;
			Total += Ly.Weight;
		}
	}
	if (!bAny) Output.ResetToRefPose();
	return true;
}
