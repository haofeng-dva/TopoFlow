"""Generate a Unity-ready folder and editor-side import validator."""

import json
from pathlib import Path

UNITY_IMPORTER = r'''using System.IO;
using UnityEditor;
using UnityEngine;

namespace TopoFlow.Editor
{
    public static class TopoFlowAssetImporter
    {
        [MenuItem("TopoFlow/Validate Selected Asset")]
        public static void ValidateSelectedAsset()
        {
            var path = AssetDatabase.GetAssetPath(Selection.activeObject);
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) { Debug.LogError("TopoFlow: select an imported FBX model."); return; }
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var renderers = model == null ? null : model.GetComponentsInChildren<MeshRenderer>(true);
            if (model == null || renderers == null || renderers.Length == 0) { Debug.LogError("TopoFlow: FBX has no renderable mesh."); return; }
            Debug.Log($"TopoFlow: validation passed for {Path.GetFileName(path)}; scale={importer.globalScale}, normals={importer.importNormals}.");
        }
    }
}
'''


def write_unity_metadata(engine_dir: str, asset_name: str, files: list[str], preset: dict) -> list[str]:
    root = Path(engine_dir)
    editor_dir = root / "Editor"
    editor_dir.mkdir(parents=True, exist_ok=True)
    importer_path = editor_dir / "TopoFlowAssetImporter.cs"
    importer_path.write_text(UNITY_IMPORTER, encoding="utf-8")
    manifest_path = root / "topoflow_unity.json"
    manifest_path.write_text(json.dumps({
        "asset_name": asset_name,
        "preset": preset,
        "files": files,
        "instructions": [
            "Copy this folder under a Unity or Tuanjie Engine project's Assets directory.",
            "Select the FBX and run TopoFlow/Validate Selected Asset.",
            "Use the normal map as Texture Type: Normal map.",
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return [str(importer_path), str(manifest_path)]
