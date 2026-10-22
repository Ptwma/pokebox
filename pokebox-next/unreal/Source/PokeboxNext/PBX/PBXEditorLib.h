// Pokebox Next — small C++ helpers for the editor build scripts (Content/Python/pbx_build.py).
#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "PBXEditorLib.generated.h"

class UStaticMesh;

UCLASS()
class UPBXEditorLib : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** adds one hierarchical-instanced mesh component holding these world-space instances to Host (forests, meadow
	 *  grass: thousands of copies drawn in a few calls, culled and LOD'ed per cluster). Returns the instance count. */
	UFUNCTION(BlueprintCallable, Category = "PBX")
	static int32 AddInstances(AActor* Host, UStaticMesh* Mesh, const TArray<FTransform>& Instances, float CullStart, float CullEnd, bool bCollision, bool bShadow);
};
