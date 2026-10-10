// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class PokeboxNext : ModuleRules
{
	public PokeboxNext(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate",
			"SlateCore",
			"Json",
			"JsonUtilities",
			"AssetRegistry"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"PokeboxNext",
			"PokeboxNext/PBX",
			"PokeboxNext/Variant_Platforming",
			"PokeboxNext/Variant_Platforming/Animation",
			"PokeboxNext/Variant_Combat",
			"PokeboxNext/Variant_Combat/AI",
			"PokeboxNext/Variant_Combat/Animation",
			"PokeboxNext/Variant_Combat/Gameplay",
			"PokeboxNext/Variant_Combat/Interfaces",
			"PokeboxNext/Variant_Combat/UI",
			"PokeboxNext/Variant_SideScrolling",
			"PokeboxNext/Variant_SideScrolling/AI",
			"PokeboxNext/Variant_SideScrolling/Gameplay",
			"PokeboxNext/Variant_SideScrolling/Interfaces",
			"PokeboxNext/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
