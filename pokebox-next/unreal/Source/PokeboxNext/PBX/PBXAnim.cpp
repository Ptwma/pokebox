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
			TArray<FAssetData> All = Scan(TEXT("/Game/PBX/Characters/Anim"));
			All.Append(Scan(TEXT("/Game/PBX/Characters/Retarget/Anim")));   // the same clips retargeted to the Fab boy ("<name>_Boy", tools: pbx_retarget.py)
			All.Append(Scan(TEXT("/Game/PBX/Characters/Retarget/Anim_MH")));  // ... and to the MetaHuman body ("<name>_MH", pbx_retarget.run_target)
			for (const FAssetData& A : All)
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
	LoadLocomotion();
	for (int32 i = 0; i < FPBXAnimProxy::NumLayers; i++) State[i].Time = FMath::FRand() * 2.f;  // NPCs don't idle in sync
}

UAnimSequence* UPBXAnimInstance::Clip(const FString& Short) const
{
	if (!AnimSuffix.IsEmpty()) if (UAnimSequence* S = PBXAssets::Anim(Short + AnimSuffix)) return S;
	return PBXAssets::Anim(Short);
}

void UPBXAnimInstance::LoadLocomotion()
{
	Idle = Clip(TEXT("Idle_Loop")); Walk = Clip(TEXT("Walk_Loop")); Jog = Clip(TEXT("Jog_Fwd_Loop"));
	Sprint = Clip(TEXT("Sprint_Loop")); Fall = Clip(TEXT("Jump_Loop"));
}

void UPBXAnimInstance::SetSuffix(const FString& S)
{
	if (S == AnimSuffix && Idle) return;
	AnimSuffix = S; Action = nullptr; ActionTarget = 0.f; LoadLocomotion();
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
	const float Sv = Speed / FMath::Max(.5f, StrideScale);   // speed in "clip body" units
	const float Rates[4] = { 1.f, FMath::Clamp(Sv / 140.f, .7f, 1.6f), FMath::Clamp(Sv / 380.f, .75f, 1.6f), FMath::Clamp(Sv / 600.f, .8f, 1.6f) };
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
	{
		for (int32 i = 0; i < NumLayers; i++) L[i] = I->State[i];
		Style = I->Style;
	}
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
	if (Style.bRelaxHands) RelaxHands(Output);
	Stylize(Output);
	return true;
}

// Owner 2026-11-06: "the hands are not right". The UAL finger tracks retargeted onto the MetaHuman body twist the fingers
// (claws, fingers bent sideways). Replace every finger with a relaxed hand built from the MetaHuman REF pose: each finger
// joint curls about the knuckle line (index→pinky), toward the palm side (where the thumb tip is), more for the outer
// fingers. Axes are derived from the ref pose at runtime, so left and right hands need no hand-tuned signs.
void FPBXAnimProxy::RelaxHands(FPoseContext& Output) const
{
	const FBoneContainer& BC = Output.Pose.GetBoneContainer();
	auto Cmp = [&](const FString& N) -> int32
	{
		const int32 Mesh = BC.GetPoseBoneIndexForBoneName(FName(*N)); if (Mesh == INDEX_NONE) return INDEX_NONE;
		return BC.MakeCompactPoseIndex(FMeshPoseBoneIndex(Mesh)).GetInt();
	};
	auto RefComp = [&](int32 I) -> FTransform     // component-space ref transform (walk up the parents)
	{
		FTransform T = FTransform::Identity;
		while (I >= 0) { T = T * BC.GetRefPoseTransform(FCompactPoseBoneIndex(I)); I = BC.GetParentBoneIndex(FCompactPoseBoneIndex(I)).GetInt(); }
		return T;
	};
	static const TCHAR* Fingers[4] = { TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky") };
	static const float Curl[4][3] = { { 14, 22, 14 }, { 18, 28, 16 }, { 22, 32, 18 }, { 26, 36, 20 } };
	for (const TCHAR* Side : { TEXT("l"), TEXT("r") })
	{
		const int32 I1 = Cmp(FString::Printf(TEXT("index_01_%s"), Side)), P1 = Cmp(FString::Printf(TEXT("pinky_01_%s"), Side)), T3 = Cmp(FString::Printf(TEXT("thumb_03_%s"), Side));
		if (I1 == INDEX_NONE || P1 == INDEX_NONE) continue;
		const FVector KnIdx = RefComp(I1).GetLocation(), KnPky = RefComp(P1).GetLocation();
		const FVector Knuckles = (KnPky - KnIdx).GetSafeNormal();
		const FVector Thumb = T3 != INDEX_NONE ? RefComp(T3).GetLocation() - KnIdx : FVector::ZeroVector;
		for (int32 f = 0; f < 4; f++)
			for (int32 k = 1; k <= 3; k++)
			{
				const int32 B = Cmp(FString::Printf(TEXT("%s_%02d_%s"), Fingers[f], k, Side)); if (B == INDEX_NONE) continue;
				const FCompactPoseBoneIndex BI(B);
				const int32 C = Cmp(FString::Printf(TEXT("%s_%02d_%s"), Fingers[f], k + 1, Side));
				const FTransform CB = RefComp(B);
				FVector Dir = C != INDEX_NONE ? (RefComp(C).GetLocation() - CB.GetLocation()) : CB.GetRotation().GetAxisX() * (Side[0] == 'r' ? -1.f : 1.f);
				Dir = Dir.GetSafeNormal();
				FVector Axis = (Knuckles - Dir * FVector::DotProduct(Knuckles, Dir)).GetSafeNormal();
				if (Axis.IsNearlyZero()) { Output.Pose[BI].SetRotation(BC.GetRefPoseTransform(BI).GetRotation()); continue; }
				FVector Palm = Thumb - Dir * FVector::DotProduct(Thumb, Dir) - Axis * FVector::DotProduct(Thumb, Axis);
				if (FVector::DotProduct(FVector::CrossProduct(Axis, Dir), Palm) < 0.f) Axis = -Axis;   // curl toward the palm
				const int32 Par = BC.GetParentBoneIndex(BI).GetInt();
				const FQuat ParRot = Par >= 0 ? RefComp(Par).GetRotation() : FQuat::Identity;
				const FVector LocalAxis = ParRot.Inverse().RotateVector(Axis);
				Output.Pose[BI].SetRotation(FQuat(LocalAxis, FMath::DegreesToRadians(Curl[f][k - 1])) * BC.GetRefPoseTransform(BI).GetRotation());
			}
		for (int32 k = 1; k <= 3; k++)   // thumb and metacarpals: the ref pose (relaxed, not twisted)
		{
			const int32 B = Cmp(FString::Printf(TEXT("thumb_%02d_%s"), k, Side));
			if (B != INDEX_NONE) Output.Pose[FCompactPoseBoneIndex(B)].SetRotation(BC.GetRefPoseTransform(FCompactPoseBoneIndex(B)).GetRotation());
		}
		for (int32 f = 0; f < 4; f++)
		{
			const int32 B = Cmp(FString::Printf(TEXT("%s_metacarpal_%s"), Fingers[f], Side));
			if (B != INDEX_NONE) Output.Pose[FCompactPoseBoneIndex(B)].SetRotation(BC.GetRefPoseTransform(FCompactPoseBoneIndex(B)).GetRotation());
		}
	}
}

// Cartoon proportions on the Quaternius "superhero" bodies without touching the meshes or the animations:
// per-bone scales on the final local pose. Rules give the wanted COMPONENT-space scale; parents' scales are divided
// out (Unreal composes scale per axis), so e.g. hands stay round although the forearms are slimmed.
// Thickness = the two axes across the bone (the bone's length axis is the direction to its child in the ref pose).
// Hair, eyes, brows and the 3D clothes follow through the leader pose, so caps and hats grow with the head.
void FPBXAnimProxy::Stylize(FPoseContext& Output) const
{
	if (Style.Head == 1.f && Style.Limb == 1.f) return;
	struct FRule { const TCHAR* Bone; const TCHAR* Child; float Uni; float Thick; };
	const FRule Rules[] = {
		{ TEXT("spine_03"), TEXT("neck_01"), 1.f, Style.Chest },
		{ TEXT("clavicle_l"), nullptr, 1.f, 1.f }, { TEXT("clavicle_r"), nullptr, 1.f, 1.f },
		{ TEXT("neck_01"), TEXT("Head"), 1.f, Style.Neck },
		{ TEXT("Head"), nullptr, Style.Head, 1.f },
		{ TEXT("upperarm_l"), TEXT("lowerarm_l"), 1.f, Style.Limb }, { TEXT("upperarm_r"), TEXT("lowerarm_r"), 1.f, Style.Limb },
		{ TEXT("lowerarm_l"), TEXT("hand_l"), 1.f, Style.Limb }, { TEXT("lowerarm_r"), TEXT("hand_r"), 1.f, Style.Limb },
		{ TEXT("hand_l"), nullptr, Style.Hand, 1.f }, { TEXT("hand_r"), nullptr, Style.Hand, 1.f },
		{ TEXT("thigh_l"), TEXT("calf_l"), 1.f, Style.Leg }, { TEXT("thigh_r"), TEXT("calf_r"), 1.f, Style.Leg },
		{ TEXT("calf_l"), TEXT("foot_l"), 1.f, Style.Leg }, { TEXT("calf_r"), TEXT("foot_r"), 1.f, Style.Leg },
		{ TEXT("foot_l"), nullptr, Style.Foot, 1.f }, { TEXT("foot_r"), nullptr, Style.Foot, 1.f } };
	const FBoneContainer& BC = Output.Pose.GetBoneContainer();
	auto Compact = [&](const TCHAR* N) -> int32
	{
		if (!N) return INDEX_NONE;
		const int32 Mesh = BC.GetPoseBoneIndexForBoneName(FName(N)); if (Mesh == INDEX_NONE) return INDEX_NONE;
		return BC.MakeCompactPoseIndex(FMeshPoseBoneIndex(Mesh)).GetInt();
	};
	const int32 Num = Output.Pose.GetNumBones();
	TArray<FVector> Want; Want.Init(FVector::ZeroVector, Num);     // zero = no rule: inherit
	for (const FRule& R : Rules)
	{
		const int32 B = Compact(R.Bone); if (B == INDEX_NONE) continue;
		FVector W(R.Uni);
		const int32 C = Compact(R.Child);
		if (C != INDEX_NONE && R.Thick != 1.f)
		{
			const FVector T = BC.GetRefPoseTransform(FCompactPoseBoneIndex(C)).GetTranslation().GetAbs();
			const int32 Ax = T.X >= T.Y && T.X >= T.Z ? 0 : T.Y >= T.Z ? 1 : 2;
			W = FVector(R.Thick); W[Ax] = R.Uni;
		}
		Want[B] = W;
	}
	TArray<FVector> Acc; Acc.Init(FVector::OneVector, Num);       // accumulated component-space scale (per axis)
	for (int32 i = 0; i < Num; i++)
	{
		const FCompactPoseBoneIndex I(i);
		const int32 P = BC.GetParentBoneIndex(I).GetInt();
		const FVector Parent = P >= 0 ? Acc[P] : FVector::OneVector;
		FTransform& T = Output.Pose[I];
		if (!Want[i].IsZero()) T.SetScale3D(Want[i] / Parent);
		Acc[i] = Parent * T.GetScale3D();
	}
}
