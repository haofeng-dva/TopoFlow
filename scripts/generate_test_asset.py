"""生成测试用 OBJ 资产"""
import os
import trimesh
import trimesh.creation

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "test_assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    print("生成测试资产...")

    # 简单角色: 头 + 躯干 + 四肢
    head = trimesh.creation.uv_sphere(radius=0.5, count=[16, 12])
    head.apply_translation([0, 2.2, 0])

    torso = trimesh.creation.cylinder(radius=0.4, height=0.8, sections=10)
    torso.apply_translation([0, 1.2, 0])

    arm = trimesh.creation.cylinder(radius=0.15, height=0.6, sections=8)
    arm_l = arm.copy().apply_translation([-0.5, 1.5, 0])
    arm_r = arm.copy().apply_translation([0.5, 1.5, 0])

    leg = trimesh.creation.cylinder(radius=0.2, height=0.6, sections=8)
    leg_l = leg.copy().apply_translation([-0.2, 0.2, 0])
    leg_r = leg.copy().apply_translation([0.2, 0.2, 0])

    combined = trimesh.util.concatenate([head, torso, arm_l, arm_r, leg_l, leg_r])
    path = os.path.join(OUTPUT_DIR, "test_mannequin.obj")
    combined.export(path)

    print(f"  已生成: {path}")
    print(f"  顶点: {len(combined.vertices)}, 三角面: {len(combined.faces)}")


if __name__ == "__main__":
    main()
