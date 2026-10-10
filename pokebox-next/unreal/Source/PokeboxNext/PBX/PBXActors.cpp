#include "PBX/PBXActors.h"
#include "PBX/PBXAnim.h"
#include "PBX/PBXCore.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "AIController.h"

// The Quaternius glTF characters face +Y after import; Unreal characters face +X.
static const float PBX_MESH_YAW = -90.f;
static const float PBX_CAPSULE_HALF = 90.f;

float PBXWorld::GroundZ(const UWorld* W, const FVector& P, float Up, float Down, float Fallback)
{
	if (!W) return Fallback;
	FHitResult H;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(PBXGround), true);
	if (W->LineTraceSingleByObjectType(H, P + FVector(0, 0, Up), P - FVector(0, 0, Down), FCollisionObjectQueryParams(ECC_WorldStatic), Q)) return H.ImpactPoint.Z;
	return Fallback;
}

// ------------------------------------------------------------------ characters
APBXCharacterBase::APBXCharacterBase()
{
	PrimaryActorTick.bCanEverTick = true;
	GetCapsuleComponent()->InitCapsuleSize(34.f, PBX_CAPSULE_HALF);
	GetMesh()->SetRelativeLocationAndRotation(FVector(0, 0, -PBX_CAPSULE_HALF), FRotator(0, PBX_MESH_YAW, 0));
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->bRenderCustomDepth = false;
	Eyes = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Eyes")); Eyes->SetupAttachment(GetMesh());
	Brows = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Brows")); Brows->SetupAttachment(GetMesh());
	Hair = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Hair")); Hair->SetupAttachment(GetMesh());
	Clothes = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Clothes")); Clothes->SetupAttachment(GetMesh());
	for (USkeletalMeshComponent* C : { Eyes.Get(), Brows.Get(), Hair.Get(), Clothes.Get() }) C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* M = GetCharacterMovement();
	M->bOrientRotationToMovement = true; M->RotationRate = FRotator(0, 600, 0);
	M->MaxWalkSpeed = 170.f; M->BrakingDecelerationWalking = 1600.f; M->JumpZVelocity = 460.f; M->AirControl = .4f;
	M->MaxStepHeight = 50.f; M->SetWalkableFloorAngle(50.f);
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
}

UPBXAnimInstance* APBXCharacterBase::Anim() const { return Cast<UPBXAnimInstance>(GetMesh()->GetAnimInstance()); }

void APBXCharacterBase::ApplyLook(const FString& BodyKind, const FString& HairName, float Scale, const FString& Outfit, FLinearColor HairColor)
{
	const bool bBoy = BodyKind == TEXT("boy");
	const bool bMale = BodyKind != TEXT("f");
	bMaleLook = bMale;
	USkeletalMesh* B = nullptr;
	const FString Dir = bMale ? TEXT("/Game/PBX/Characters/Superhero_Male_FullBody/SkeletalMeshes/") : TEXT("/Game/PBX/Characters/Superhero_Female_FullBody/SkeletalMeshes/");
	auto Load = [&](const FString& N) { return LoadObject<USkeletalMesh>(nullptr, *(Dir + N + TEXT(".") + N)); };
	if (bBoy) B = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Fab/Free_Stylized_Boy_Character/boy1.boy1"));
	if (!B) B = Load(bMale ? TEXT("SuperHero_Male") : TEXT("Superhero_Female"));
	const bool bQ = !bBoy || !B || !B->GetPathName().Contains(TEXT("Stylized_Boy"));
	if (B)
	{
		GetMesh()->SetSkeletalMesh(B);
		GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
		GetMesh()->SetAnimInstanceClass(UPBXAnimInstance::StaticClass());
	}
	else UE_LOG(LogTemp, Error, TEXT("[PBX] body mesh missing (%s)"), *BodyKind);
	// the stylized boy is a child model (1.17 m): scale the mesh, keep the capsule; feet stay on the capsule bottom
	GetMesh()->SetRelativeScale3D(FVector(bQ ? 1.f : 1.42f));
	Eyes->SetSkeletalMesh(bQ ? Load(TEXT("Eyes")) : nullptr); Brows->SetSkeletalMesh(bQ ? Load(TEXT("Eyebrows")) : nullptr);
	USkeletalMesh* H = nullptr;
	if (bQ && !HairName.IsEmpty()) H = Cast<USkeletalMesh>(PBXAssets::FindByName(TEXT("/Game/PBX/Characters/Hair"), HairName, USkeletalMesh::StaticClass()));
	Hair->SetSkeletalMesh(H); Hair->SetVisibility(H != nullptr);
	USkeletalMesh* C = nullptr;
	if (bQ && !Outfit.IsEmpty()) C = Cast<USkeletalMesh>(PBXAssets::FindByName(TEXT("/Game/PBX/Characters/Clothes"), TEXT("SK_Cloth_") + Outfit, USkeletalMesh::StaticClass()));
	Clothes->SetSkeletalMesh(C); Clothes->SetVisibility(C != nullptr);
	if (C)
		if (UMaterialInterface* CM = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/PBX/Materials/M_PBX_Cloth.M_PBX_Cloth")))
		{
			const FString PN = TEXT("T_ClothPal_") + Outfit;
			UTexture2D* Pal = LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("/Game/PBX/Characters/Clothes/Pal/%s.%s"), *PN, *PN));
			for (int32 i = 0; i < Clothes->GetNumMaterials(); i++)
			{
				UMaterialInstanceDynamic* D = UMaterialInstanceDynamic::Create(CM, Clothes);
				if (Pal) D->SetTextureParameterValue(TEXT("Pal"), Pal);
				Clothes->SetMaterial(i, D);
			}
		}
	for (USkeletalMeshComponent* X : { Eyes.Get(), Brows.Get(), Hair.Get(), Clothes.Get() }) X->SetLeaderPoseComponent(GetMesh());
	// body paint under the clothes (tools/outfits.py): same palette, so seams between garments never show bare skin
	if (bQ && !Outfit.IsEmpty())
	{
		const FString N = TEXT("T_Outfit_") + Outfit;
		if (UTexture2D* T = LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("/Game/PBX/Characters/Outfits/%s.%s"), *N, *N)))
			if (UMaterialInstanceDynamic* MID = GetMesh()->CreateAndSetMaterialInstanceDynamic(0)) MID->SetTextureParameterValue(TEXT("BaseColorTexture"), T);
	}
	if (HairColor.A > 0.f && H)
		for (int32 i = 0; i < Hair->GetNumMaterials(); i++)
			if (UMaterialInstanceDynamic* MID = Hair->CreateAndSetMaterialInstanceDynamic(i)) MID->SetVectorParameterValue(TEXT("BaseColorFactor"), HairColor);
	SetActorScale3D(FVector(Scale));
}

void APBXCharacterBase::PlayAction(const FString& Short, bool bLoop, float Blend) { if (UPBXAnimInstance* A = Anim()) A->PlayAction(PBXAssets::Anim(Short), bLoop, Blend); }
void APBXCharacterBase::StopAction(float Blend) { if (UPBXAnimInstance* A = Anim()) A->StopAction(Blend); }
void APBXCharacterBase::SetIdleAnim(const FString& Short) { if (UPBXAnimInstance* A = Anim()) A->SetIdle(PBXAssets::Anim(Short)); }

void APBXCharacterBase::FaceTowards(const FVector& P, bool bInstant)
{
	const FVector D = P - GetActorLocation(); if (D.Size2D() < 1.f) return;
	TurnYaw = D.Rotation().Yaw;
	if (bInstant) { SetActorRotation(FRotator(0, TurnYaw, 0)); bTurning = false; }
	else bTurning = true;
}

void APBXCharacterBase::Tick(float Dt)
{
	Super::Tick(Dt);
	if (bTurning)
	{
		const float Y = FMath::FixedTurn(GetActorRotation().Yaw, TurnYaw, 420.f * Dt);
		SetActorRotation(FRotator(0, Y, 0));
		if (FMath::Abs(FRotator::NormalizeAxis(Y - TurnYaw)) < 1.f) bTurning = false;
	}
}

APBXPlayer::APBXPlayer()
{
	Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("Boom"));
	Boom->SetupAttachment(RootComponent);
	Boom->TargetArmLength = 430.f; Boom->bUsePawnControlRotation = true; Boom->SocketOffset = FVector(0, 40, 60);
	Boom->bEnableCameraLag = true; Boom->CameraLagSpeed = 12.f; Boom->ProbeSize = 14.f;
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Boom, USpringArmComponent::SocketName); Camera->bUsePawnControlRotation = false; Camera->FieldOfView = 75.f;
	GetCharacterMovement()->MaxWalkSpeed = 380.f;
	AutoPossessAI = EAutoPossessAI::Disabled;
}

void APBXPlayer::SetRunning(bool bRun) { bRunning = bRun; GetCharacterMovement()->MaxWalkSpeed = bRun ? 640.f : 380.f; }
void APBXPlayer::Zoom(float D) { Boom->TargetArmLength = FMath::Clamp(Boom->TargetArmLength - D * 40.f, 220.f, 760.f); }

APBXNPC::APBXNPC()
{
	Marker = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Marker"));
	Marker->SetupAttachment(RootComponent);
	Marker->SetRelativeLocation(FVector(0, 0, 135)); Marker->SetHorizontalAlignment(EHTA_Center); Marker->SetVerticalAlignment(EVRTA_TextCenter);
	Marker->SetText(FText::FromString(TEXT("!"))); Marker->SetWorldSize(70.f); Marker->SetTextRenderColor(FColor(255, 214, 40));
	Marker->SetHiddenInGame(true); Marker->SetCastShadow(false);
}

void APBXNPC::SetMarker(bool bOn) { Marker->SetHiddenInGame(!bOn); }

void APBXNPC::ReturnToIdle()
{
	StopAction(.3f);
	if (!IdleAnim.IsEmpty() && IdleAnim != TEXT("Idle_Loop")) PlayAction(IdleAnim, true, .4f);
	TurnYaw = HomeYaw; bTurning = true;
}

void APBXNPC::WalkTo(const FVector& G, TFunction<void()> Done)
{
	StopAction(.2f); bWalking = true; WalkGoal = G; WalkDone = MoveTemp(Done); WalkT = 0.f;
}

void APBXNPC::Tick(float Dt)
{
	Super::Tick(Dt);
	if (!Marker->bHiddenInGame)
	{
		Marker->SetRelativeLocation(FVector(0, 0, 135 + 8 * FMath::Sin(GetWorld()->TimeSeconds * 4.f)));
		if (APlayerCameraManager* PC = UGameplayStatics::GetPlayerCameraManager(this, 0))
			Marker->SetWorldRotation(FRotator(0, (PC->GetCameraLocation() - Marker->GetComponentLocation()).Rotation().Yaw, 0));
	}
	if (bWalking)
	{
		WalkT += Dt;
		const FVector D = WalkGoal - GetActorLocation();
		if (D.Size2D() < 70.f || WalkT > 14.f)
		{
			bWalking = false;
			if (WalkT > 14.f) SetActorLocation(WalkGoal + FVector(0, 0, PBX_CAPSULE_HALF), false, nullptr, ETeleportType::TeleportPhysics);
			GetCharacterMovement()->StopMovementImmediately();
			if (WalkDone) { TFunction<void()> F = MoveTemp(WalkDone); F(); }
		}
		else AddMovementInput(FVector(D.X, D.Y, 0).GetSafeNormal(), 1.f);
	}
}

// ------------------------------------------------------------------ Echoes
APBXEcho::APBXEcho()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root")); SetRootComponent(Root);
	Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("Pivot")); Pivot->SetupAttachment(Root);
	Paper = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Paper")); Paper->SetupAttachment(Pivot);
	Paper->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Paper->SetRelativeRotation(FRotator(0, -90.f, 0));   // SM_EchoCard faces +Y -> turn it to face +X (the pivot looks at the camera)
	Paper->bRenderCustomDepth = false;
}

bool APBXEcho::Setup(FName Card, float Height)
{
	CardId = Card; HeightCm = Height;
	UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/PBX/Meshes/SM_EchoCard.SM_EchoCard"));
	UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/PBX/Materials/M_PBX_Echo.M_PBX_Echo"));
	const FPBXCardDef* C = PBXData::Card(Card);
	UTexture2D* Tex = C ? LoadObject<UTexture2D>(nullptr, *C->EchoTexturePath()) : nullptr;
	if (!M || !Mat || !Tex) { UE_LOG(LogTemp, Error, TEXT("[PBX] echo assets missing for %s (mesh %d mat %d tex %d)"), *Card.ToString(), M != nullptr, Mat != nullptr, Tex != nullptr); }
	if (M) Paper->SetStaticMesh(M);
	if (Mat) { MID = UMaterialInstanceDynamic::Create(Mat, this); if (Tex) MID->SetTextureParameterValue(TEXT("Tex"), Tex); Paper->SetMaterial(0, MID); }
	Paper->SetRelativeScale3D(FVector(Height / 100.f));
	return M && Mat && Tex;
}

void APBXEcho::PlaceAt(const FVector& P)
{
	SetActorLocation(FVector(P.X, P.Y, PBXWorld::GroundZ(GetWorld(), P, 300.f, 1500.f, P.Z)));
}

void APBXEcho::Flash(const FLinearColor& C, float S) { FlashT = .35f; FlashCol = C; FlashStrength = S; }
void APBXEcho::Lunge(const FVector& Dir, float Dist) { LungeT = 0.f; LungeDir = Dir.GetSafeNormal2D(); LungeDist = Dist; }
void APBXEcho::Hurt() { HurtT = 0.f; Flash(FLinearColor(1, .25f, .2f), 2.5f); }
void APBXEcho::SetFaint(bool b) { bFaint = b; if (!b) FaintK = 0.f; }
void APBXEcho::PopIn() { PopT = 0.f; }

void APBXEcho::Tick(float Dt)
{
	Super::Tick(Dt);
	T += Dt;
	const UWorld* W = GetWorld();
	FVector Loc = GetActorLocation(); float Moving = 0.f;
	auto StepTowards = [&](const FVector& Target, float MaxSpeed)
	{
		FVector D = Target - Loc; D.Z = 0; const float Dist = D.Size();
		if (Dist > 5.f)
		{
			const float Sp = FMath::Min(MaxSpeed, Dist * 3.f);
			Loc += D / Dist * FMath::Min(Dist, Sp * Dt); Moving = FMath::Clamp(Sp / 250.f, 0.f, 1.f);
		}
		Loc.Z = PBXWorld::GroundZ(W, Loc, 200.f, 600.f, Loc.Z);
	};
	if (!bFaint)
	{
		if (Mode == EMode::Follow && FollowTarget.IsValid())
		{
			const AActor* A = FollowTarget.Get();
			const FVector Want = A->GetActorLocation() - A->GetActorForwardVector() * 130.f + A->GetActorRightVector() * 95.f;
			const float Dist = FVector::Dist2D(Want, Loc);
			if (Dist > 900.f) Loc = FVector(Want.X, Want.Y, PBXWorld::GroundZ(W, Want, 300.f, 1500.f, Loc.Z)); // teleported (doors)
			else if (Dist > 60.f) StepTowards(Want, FMath::Clamp(Dist * 2.2f, 150.f, 700.f));
		}
		else if (Mode == EMode::Wander)
		{
			if (WanderWait > 0.f) WanderWait -= Dt;
			else
			{
				if (FVector::Dist2D(Goal, Loc) < 20.f || Goal.IsZero())
				{
					Goal = FVector(FMath::FRandRange(WanderBox.Min.X, WanderBox.Max.X), FMath::FRandRange(WanderBox.Min.Y, WanderBox.Max.Y), Loc.Z);
					WanderWait = FMath::FRandRange(.8f, 3.f);
				}
				else StepTowards(Goal, 120.f);
			}
		}
	}
	SetActorLocation(Loc);

	// face the camera (a paper figure turning to look at you)
	if (APlayerCameraManager* PC = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		const float Want = (PC->GetCameraLocation() - Loc).Rotation().Yaw;
		CurYaw = FMath::FixedTurn(CurYaw, Want, 720.f * Dt);
	}
	// hop / breathe / squash, lunge, hurt shake, pop-in, faint
	HopT += Dt * (6.f + 8.f * Moving);
	const float Hop = FMath::Abs(FMath::Sin(HopT * 1.6f)) * (6.f + 26.f * Moving);
	const float Breath = 1.f + .025f * FMath::Sin(T * 3.1f);
	FVector Off(0, 0, Hop);
	if (LungeT >= 0.f)
	{
		LungeT += Dt; const float k = LungeT / .38f;
		if (k >= 1.f) LungeT = -1.f; else Off += LungeDir * LungeDist * FMath::Sin(k * PI);
	}
	if (HurtT >= 0.f)
	{
		HurtT += Dt; if (HurtT > .35f) HurtT = -1.f; else Off += FVector(FMath::Sin(HurtT * 90.f) * 9.f, FMath::Cos(HurtT * 77.f) * 9.f, 0);
	}
	PopT = FMath::Min(1.f, PopT + Dt / .4f);
	const float Pop = PopT >= 1.f ? 1.f : FMath::Sin(PopT * PI * .5f) * (1.f + .25f * FMath::Sin(PopT * PI));
	FaintK = FMath::FInterpTo(FaintK, bFaint ? 1.f : 0.f, Dt, 5.f);
	Pivot->SetRelativeLocation(Off);
	Pivot->SetWorldRotation(FRotator(0, CurYaw, FaintK * 82.f));
	Pivot->SetRelativeScale3D(FVector(Pop, Pop, Pop * Breath * (1.f - .06f * Moving * FMath::Abs(FMath::Cos(HopT * 1.6f)))));
	if (MID)
	{
		FlashT = FMath::Max(0.f, FlashT - Dt);
		MID->SetScalarParameterValue(TEXT("Flash"), FlashStrength * FlashT / .35f);
		MID->SetVectorParameterValue(TEXT("FlashColor"), FlashCol);
	}
}
