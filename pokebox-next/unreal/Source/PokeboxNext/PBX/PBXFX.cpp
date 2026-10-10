#include "PBX/PBXFX.h"
#include "PBX/PBXCore.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"
#include "UObject/ConstructorHelpers.h"

APBXFX::APBXFX()
{
	PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickGroup = TG_PostUpdateWork;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	auto Make = [this](const TCHAR* Name, const TCHAR* Mat) -> UInstancedStaticMeshComponent*
	{
		UInstancedStaticMeshComponent* C = CreateDefaultSubobject<UInstancedStaticMeshComponent>(Name);
		C->SetupAttachment(GetRootComponent());
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision); C->SetCastShadow(false); C->bReceivesDecals = false;
		C->SetMobility(EComponentMobility::Movable); C->NumCustomDataFloats = 4; C->SetCanEverAffectNavigation(false);
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
		if (Plane.Succeeded()) C->SetStaticMesh(Plane.Object);
		C->SetMaterial(0, LoadObject<UMaterialInterface>(nullptr, Mat));
		return C;
	};
	Dots = Make(TEXT("Dots"), TEXT("/Game/PBX/Materials/Inst/MI_FX_Dot.MI_FX_Dot"));
	Stars = Make(TEXT("Stars"), TEXT("/Game/PBX/Materials/Inst/MI_FX_Star.MI_FX_Star"));
}

void APBXFX::Clear() { Ps.Reset(); Beams.Reset(); bAmb = false; Rebuild(); }

void APBXFX::Burst(const FVector& P, FLinearColor C, int32 N, float Speed, float Size, float Life, float Gravity, float UpBias, uint8 Shape, float Drag)
{
	for (int32 i = 0; i < N; i++)
	{
		FP X; X.P = P + FMath::VRand() * Size * .3f;
		FVector D = FMath::VRand(); D.Z = FMath::Abs(D.Z) * UpBias + D.Z * (1.f - UpBias); D.Normalize();
		X.V = D * Speed * FMath::FRandRange(.35f, 1.f);
		X.C = C * FMath::FRandRange(.8f, 1.2f); X.C.A = 1.f;
		X.Size = Size * FMath::FRandRange(.5f, 1.25f); X.Life = Life * FMath::FRandRange(.6f, 1.2f);
		X.Grav = Gravity; X.Drag = Drag; X.Spin = FMath::FRandRange(-6.f, 6.f); X.Rot = FMath::FRand() * 6.28f; X.Shape = Shape;
		Add(X);
	}
}

void APBXFX::TypedHit(const FVector& P, const FString& Type, float Power)
{
	const FLinearColor C = PBXData::TypeColor(Type);
	const float K = FMath::Clamp(Power, .5f, 2.5f);
	const int32 N = FMath::RoundToInt(26 * K);
	if (Type == TEXT("Fire"))
	{
		Burst(P, FLinearColor(1.f, .45f, .08f), N, 420.f * K, 34.f, .9f, 260.f, .8f, 0, 1.8f);            // embers float up
		Burst(P, FLinearColor(1.f, .85f, .3f), N / 2, 650.f * K, 22.f, .45f, 0.f, .3f, 1);
	}
	else if (Type == TEXT("Water"))
	{
		Burst(P, FLinearColor(.25f, .6f, 1.f), N, 560.f * K, 30.f, .9f, -900.f, .75f, 0, 1.f);           // spray falls back
		Burst(P, FLinearColor(.8f, .95f, 1.f), N / 2, 380.f * K, 18.f, .6f, -600.f, .5f, 0);
	}
	else if (Type == TEXT("Grass"))
	{
		Burst(P, FLinearColor(.35f, .9f, .25f), N, 380.f * K, 36.f, 1.2f, -120.f, .5f, 1, 2.2f);         // leaves drift
		Burst(P, FLinearColor(.85f, 1.f, .4f), N / 2, 300.f * K, 20.f, .8f, -60.f, .5f, 0);
	}
	else if (Type == TEXT("Lightning"))
	{
		Burst(P, FLinearColor(1.f, .95f, .25f), N, 1100.f * K, 26.f, .32f, 0.f, .2f, 1, 4.f);            // fast short sparks
		Burst(P, FLinearColor(1.f, 1.f, .8f), N / 3, 200.f, 70.f, .18f, 0.f, 0.f, 0);
	}
	else if (Type == TEXT("Psychic"))
	{
		Burst(P, FLinearColor(.85f, .35f, 1.f), N, 300.f * K, 34.f, 1.f, 80.f, .3f, 1, 1.2f);
		Ring(P - FVector(0, 0, 60), FLinearColor(.9f, .5f, 1.f), 160.f * K, 24, 26.f);
	}
	else if (Type == TEXT("Fighting") || Type == TEXT("Darkness") || Type == TEXT("Metal"))
	{
		Burst(P, C * 1.3f, N, 700.f * K, 30.f, .4f, -300.f, .3f, 0, 3.f);
		Burst(P, FLinearColor(1, 1, 1), N / 3, 900.f * K, 24.f, .25f, 0.f, .1f, 1, 4.f);
	}
	else  // Colorless & others: white stars
	{
		Burst(P, FLinearColor(1.f, .97f, .85f), N, 520.f * K, 30.f, .55f, -300.f, .4f, 1, 2.5f);
		Burst(P, C * 1.2f, N / 2, 360.f * K, 22.f, .5f, -200.f, .4f, 0);
	}
	// a quick white flash core
	Burst(P, FLinearColor(1, 1, 1), 3, 30.f, 120.f * K, .14f, 0.f, 0.f, 0, 0.f);
}

void APBXFX::Beam(const FVector& From, const FVector& To, FLinearColor C, float Secs, float Size, uint8 Shape)
{
	FB B; B.From = From; B.To = To; B.C = C; B.Secs = FMath::Max(.05f, Secs); B.Size = Size; B.Shape = Shape; Beams.Add(B);
}

void APBXFX::Ring(const FVector& P, FLinearColor C, float Radius, int32 N, float Size)
{
	for (int32 i = 0; i < N; i++)
	{
		const float A = 2.f * PI * i / N; const FVector D(FMath::Cos(A), FMath::Sin(A), 0);
		FP X; X.P = P + D * 20.f; X.V = D * Radius * 2.2f + FVector(0, 0, 60); X.C = C; X.Size = Size; X.Life = .55f;
		X.Grav = 0.f; X.Drag = 2.5f; X.Spin = 3.f; X.Rot = A; X.Shape = (i % 3 == 0) ? 1 : 0; Add(X);
	}
}

void APBXFX::SetAmbient(bool bOn, const FVector& A, const FVector& B, FLinearColor C) { bAmb = bOn; AmbA = A; AmbB = B; AmbC = C; }

void APBXFX::Tick(float Dt)
{
	Super::Tick(Dt);
	Dt = FMath::Min(Dt, .05f);
	// emitters
	for (int32 i = Beams.Num() - 1; i >= 0; i--)
	{
		FB& B = Beams[i]; B.T += Dt; B.Acc += Dt * 90.f;
		const float K = FMath::Clamp(B.T / B.Secs, 0.f, 1.f);
		const FVector Head = FMath::Lerp(B.From, B.To, K) + FVector(0, 0, FMath::Sin(K * PI) * 60.f);
		while (B.Acc >= 1.f)
		{
			B.Acc -= 1.f;
			FP X; X.P = Head + FMath::VRand() * B.Size * .5f; X.V = FMath::VRand() * 60.f; X.C = B.C; X.Size = B.Size * FMath::FRandRange(.6f, 1.2f);
			X.Life = .35f; X.Grav = 0.f; X.Drag = 3.f; X.Spin = 4.f; X.Rot = 0.f; X.Shape = B.Shape; Add(X);
		}
		if (B.T >= B.Secs) Beams.RemoveAt(i);
	}
	if (bAmb)
	{
		AmbAcc += Dt * 14.f;
		while (AmbAcc >= 1.f)
		{
			AmbAcc -= 1.f;
			FP X; X.P = FVector(FMath::FRandRange(AmbA.X, AmbB.X), FMath::FRandRange(AmbA.Y, AmbB.Y), FMath::FRandRange(AmbA.Z, AmbA.Z + 60.f));
			X.V = FVector(FMath::FRandRange(-15.f, 15.f), FMath::FRandRange(-15.f, 15.f), FMath::FRandRange(40.f, 90.f)); X.C = AmbC * .55f;
			X.Size = FMath::FRandRange(6.f, 14.f); X.Life = FMath::FRandRange(2.f, 3.5f); X.Grav = 0.f; X.Drag = 0.f; X.Spin = 0.f; X.Rot = 0.f; X.Shape = 0; Add(X);
		}
	}
	for (int32 i = Ps.Num() - 1; i >= 0; i--)
	{
		FP& X = Ps[i]; X.Age += Dt;
		if (X.Age >= X.Life) { Ps.RemoveAtSwap(i); continue; }
		X.V.Z += X.Grav * Dt; X.V *= FMath::Max(0.f, 1.f - X.Drag * Dt); X.P += X.V * Dt; X.Rot += X.Spin * Dt;
	}
	Rebuild();
}

void APBXFX::Rebuild()
{
	FVector Cam = FVector::ZeroVector;
	if (APlayerCameraManager* PCM = UGameplayStatics::GetPlayerCameraManager(this, 0)) Cam = PCM->GetCameraLocation();
	TArray<FTransform> T[2]; TArray<float> D[2];
	for (const FP& X : Ps)
	{
		const float K = X.Age / X.Life;
		const float A = K < .15f ? K / .15f : 1.f - (K - .15f) / .85f;          // quick fade in, long fade out
		const float S = X.Size * (X.Shape == 1 ? (1.f - K * .5f) : (.6f + .4f * (1.f - K))) / 100.f;
		const FVector Z = (Cam - X.P).GetSafeNormal();
		FQuat Q = FRotationMatrix::MakeFromZ(Z).ToQuat() * FQuat(FVector::UpVector, X.Rot);
		const int32 k = X.Shape == 1 ? 1 : 0;
		T[k].Add(FTransform(Q, X.P, FVector(S)));
		D[k].Append({ X.C.R, X.C.G, X.C.B, FMath::Clamp(A, 0.f, 1.f) });
	}
	UInstancedStaticMeshComponent* C[2] = { Dots, Stars };
	for (int32 k = 0; k < 2; k++)
	{
		if (!C[k]) continue;
		C[k]->ClearInstances();
		if (!T[k].Num()) continue;
		C[k]->AddInstances(T[k], false, true);
		for (int32 i = 0; i < T[k].Num(); i++)
			C[k]->SetCustomData(i, TArrayView<const float>(D[k].GetData() + i * 4, 4), i == T[k].Num() - 1);
	}
}
