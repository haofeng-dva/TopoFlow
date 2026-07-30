"""Create the reusable Tuanjie Engine validation project."""

import json
from pathlib import Path


PROJECT_VERSION = "2022.3.62t11"

VALIDATOR_SOURCE = r'''using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace TopoFlow.Editor
{
    [Serializable] public class TopoFlowManifest { public string asset_name; public string[] files; }
    [Serializable] public class GateDResult
    {
        public bool passed;
        public string status;
        public string asset_name;
        public string model_path;
        public string material_path;
        public string prefab_path;
        public int mesh_count;
        public int skinned_mesh_count;
        public int bone_count;
        public int animation_clip_count;
        public int material_count;
        public bool has_uv;
        public bool uv_required;
        public bool normal_map_imported;
        public List<string> errors = new List<string>();
    }

    public static class TopoFlowBatchValidator
    {
        public static void Run()
        {
            var args = Environment.GetCommandLineArgs();
            var manifestPath = Argument(args, "-topoflowManifest");
            var resultPath = Argument(args, "-topoflowResult");
            var result = new GateDResult { status = "failed" };
            try
            {
                var manifest = JsonUtility.FromJson<TopoFlowManifest>(File.ReadAllText(manifestPath));
                result.asset_name = manifest.asset_name;
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                var modelPath = FindAssetPath(manifest.files, ".fbx");
                result.model_path = modelPath;
                ConfigureModel(modelPath);
                var normalPath = FindNamedAssetPath(manifest.files, "_normal");
                result.normal_map_imported = ConfigureNormal(normalPath);
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
                if (model == null) throw new Exception("FBX import failed");
                var meshes = model.GetComponentsInChildren<MeshFilter>(true);
                var skinnedMeshes = model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                result.mesh_count = meshes.Length;
                result.skinned_mesh_count = skinnedMeshes.Length;
                result.bone_count = CountBones(skinnedMeshes);
                result.animation_clip_count = CountAnimationClips(modelPath);
                result.has_uv = HasUv(meshes, skinnedMeshes);
                result.uv_required = HasTextureFiles(manifest.files);
                if (result.mesh_count + result.skinned_mesh_count == 0) result.errors.Add("No mesh found");
                if (result.uv_required && !result.has_uv) result.errors.Add("No UV0 found for textured asset");
                var material = CreateMaterial(manifest.asset_name, normalPath, manifest.files);
                result.material_path = AssetDatabase.GetAssetPath(material);
                result.material_count = material == null ? 0 : 1;
                result.prefab_path = CreatePrefab(manifest.asset_name, model, material);
                result.passed = result.errors.Count == 0 && result.material_count > 0;
                result.status = result.passed ? "passed" : "failed";
            }
            catch (Exception exception) { result.errors.Add(exception.ToString()); }
            Directory.CreateDirectory(Path.GetDirectoryName(resultPath));
            File.WriteAllText(resultPath, JsonUtility.ToJson(result, true));
            AssetDatabase.SaveAssets();
            EditorApplication.Exit(result.passed ? 0 : 2);
        }

        static string Argument(string[] args, string name)
        {
            var index = Array.IndexOf(args, name);
            if (index < 0 || index + 1 >= args.Length) throw new ArgumentException("Missing " + name);
            return args[index + 1];
        }

        static string FindAssetPath(string[] files, string suffix)
        {
            foreach (var file in files) if (file.EndsWith(suffix, StringComparison.OrdinalIgnoreCase)) return AbsoluteToAsset(file);
            throw new FileNotFoundException("Missing asset " + suffix);
        }

        static string FindNamedAssetPath(string[] files, string marker)
        {
            foreach (var file in files) if (file.IndexOf(marker, StringComparison.OrdinalIgnoreCase) >= 0) return AbsoluteToAsset(file);
            return "";
        }

        static string AbsoluteToAsset(string path)
        {
            var normalized = Path.GetFullPath(path).Replace('\\', '/');
            var project = Path.GetFullPath(Path.Combine(Application.dataPath, "..")).Replace('\\', '/').TrimEnd('/');
            if (!normalized.StartsWith(project + "/", StringComparison.OrdinalIgnoreCase)) throw new Exception("Asset is outside project: " + path);
            return normalized.Substring(project.Length + 1);
        }

        static void ConfigureModel(string path)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) throw new Exception("ModelImporter unavailable");
            importer.globalScale = 1f;
            importer.importNormals = ModelImporterNormals.Import;
            importer.importTangents = ModelImporterTangents.CalculateMikk;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.SaveAndReimport();
        }

        static bool ConfigureNormal(string path)
        {
            if (String.IsNullOrEmpty(path)) return false;
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null) return false;
            importer.textureType = TextureImporterType.NormalMap;
            importer.sRGBTexture = false;
            importer.SaveAndReimport();
            return true;
        }

        static bool HasUv(MeshFilter[] filters, SkinnedMeshRenderer[] skinnedMeshes)
        {
            foreach (var filter in filters) if (filter.sharedMesh != null && filter.sharedMesh.uv != null && filter.sharedMesh.uv.Length > 0) return true;
            foreach (var renderer in skinnedMeshes) if (renderer.sharedMesh != null && renderer.sharedMesh.uv != null && renderer.sharedMesh.uv.Length > 0) return true;
            return false;
        }

        static int CountBones(SkinnedMeshRenderer[] renderers)
        {
            var bones = new HashSet<Transform>();
            foreach (var renderer in renderers) foreach (var bone in renderer.bones) if (bone != null) bones.Add(bone);
            return bones.Count;
        }

        static int CountAnimationClips(string modelPath)
        {
            var count = 0;
            foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(modelPath)) if (asset is AnimationClip && !asset.name.StartsWith("__preview__")) count++;
            return count;
        }

        static bool HasTextureFiles(string[] files)
        {
            foreach (var file in files)
            {
                var extension = Path.GetExtension(file).ToLowerInvariant();
                if (extension == ".png" || extension == ".jpg" || extension == ".jpeg" || extension == ".tga") return true;
            }
            return false;
        }

        static Material CreateMaterial(string assetName, string normalPath, string[] files)
        {
            var folder = "Assets/TopoFlow/Generated";
            Directory.CreateDirectory(folder);
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            if (shader == null) throw new Exception("No compatible Lit shader found");
            var material = new Material(shader) { name = assetName + "_Material" };
            if (!String.IsNullOrEmpty(normalPath))
            {
                var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath);
                if (material.HasProperty("_BumpMap")) { material.SetTexture("_BumpMap", normal); material.EnableKeyword("_NORMALMAP"); }
            }
            var aoPath = FindNamedAssetPath(files, "_ao");
            if (!String.IsNullOrEmpty(aoPath) && material.HasProperty("_OcclusionMap")) material.SetTexture("_OcclusionMap", AssetDatabase.LoadAssetAtPath<Texture2D>(aoPath));
            var albedoPath = FindNamedAssetPath(files, "_albedo");
            if (String.IsNullOrEmpty(albedoPath)) albedoPath = FindNamedAssetPath(files, "_basecolor");
            if (!String.IsNullOrEmpty(albedoPath) && material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(albedoPath));
            if (!String.IsNullOrEmpty(albedoPath) && material.HasProperty("_MainTex")) material.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(albedoPath));
            var metallicPath = FindNamedAssetPath(files, "_metallic");
            if (!String.IsNullOrEmpty(metallicPath) && material.HasProperty("_MetallicGlossMap")) { material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(metallicPath)); material.EnableKeyword("_METALLICSPECGLOSSMAP"); }
            if (material.HasProperty("_Metallic")) material.SetFloat("_Metallic", String.IsNullOrEmpty(metallicPath) ? 0f : 1f);
            if (material.HasProperty("_Smoothness")) material.SetFloat("_Smoothness", 0.4f);
            var emissionPath = FindNamedAssetPath(files, "_emission");
            if (!String.IsNullOrEmpty(emissionPath) && material.HasProperty("_EmissionMap")) { material.SetTexture("_EmissionMap", AssetDatabase.LoadAssetAtPath<Texture2D>(emissionPath)); material.EnableKeyword("_EMISSION"); }
            var path = folder + "/" + assetName + ".mat";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        static string CreatePrefab(string assetName, GameObject model, Material material)
        {
            var instance = UnityEngine.Object.Instantiate(model);
            instance.name = assetName;
            foreach (var renderer in instance.GetComponentsInChildren<Renderer>(true)) renderer.sharedMaterial = material;
            var path = "Assets/TopoFlow/Generated/" + assetName + ".prefab";
            PrefabUtility.SaveAsPrefabAsset(instance, path);
            UnityEngine.Object.DestroyImmediate(instance);
            return path;
        }
    }
}
'''


def ensure_validation_project(project_dir: str) -> str:
    root = Path(project_dir).expanduser().resolve()
    (root / "Assets" / "TopoFlow" / "Editor").mkdir(parents=True, exist_ok=True)
    (root / "Assets" / "TopoFlow" / "Imports").mkdir(parents=True, exist_ok=True)
    (root / "Assets" / "TopoFlow" / "Generated").mkdir(parents=True, exist_ok=True)
    (root / "Packages").mkdir(parents=True, exist_ok=True)
    (root / "ProjectSettings").mkdir(parents=True, exist_ok=True)
    (root / "Assets" / "TopoFlow" / "Editor" / "TopoFlowBatchValidator.cs").write_text(VALIDATOR_SOURCE, encoding="utf-8")
    (root / "Packages" / "manifest.json").write_text(json.dumps({"dependencies": {}}, indent=2), encoding="utf-8")
    (root / "ProjectSettings" / "ProjectVersion.txt").write_text(f"m_EditorVersion: {PROJECT_VERSION}\n", encoding="utf-8")
    return str(root)
