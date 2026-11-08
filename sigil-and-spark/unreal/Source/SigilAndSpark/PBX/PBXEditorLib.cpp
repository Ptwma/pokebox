#include "PBX/PBXEditorLib.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

int32 UPBXEditorLib::AddInstances(AActor* Host, UStaticMesh* Mesh, const TArray<FTransform>& Instances, float CullStart, float CullEnd, bool bCollision, bool bShadow)
{
	if (!Host || !Mesh || Instances.Num() == 0) return 0;
	USceneComponent* Root = Host->GetRootComponent();
	if (!Root)
	{
		Root = NewObject<USceneComponent>(Host, TEXT("Root"), RF_Transactional);
		Root->CreationMethod = EComponentCreationMethod::Instance;
		Host->SetRootComponent(Root); Host->AddInstanceComponent(Root); Root->RegisterComponent();
		Root->SetWorldTransform(FTransform::Identity);
	}
	const FName N = MakeUniqueObjectName(Host, UHierarchicalInstancedStaticMeshComponent::StaticClass(), FName(*(Mesh->GetName() + TEXT("_Inst"))));
	UHierarchicalInstancedStaticMeshComponent* C = NewObject<UHierarchicalInstancedStaticMeshComponent>(Host, N, RF_Transactional);
	C->CreationMethod = EComponentCreationMethod::Instance;
	C->SetStaticMesh(Mesh);
	C->SetMobility(EComponentMobility::Static);
	C->SetupAttachment(Root);
	Host->AddInstanceComponent(C);
	C->RegisterComponent();
	C->SetCullDistances((int32)CullStart, (int32)CullEnd);
	C->SetCollisionEnabled(bCollision ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	C->SetCastShadow(bShadow);
	C->AddInstances(Instances, false, true);
	Host->MarkPackageDirty();
	return C->GetInstanceCount();
}
