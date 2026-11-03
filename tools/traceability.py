"""Rastreabilidade requisito -> testes. `python tools/traceability.py` gera docs/RASTREABILIDADE.md e falha se
alguma referência apontar para um teste que não existe."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

T = {
    "val": "tests.test_validation", "edm": "tests.test_editor_model", "rnd": "tests.test_rendering",
    "wsp": "tests.test_workspace", "int": "tests.test_interaction", "prp": "tests.test_properties",
    "exp": "tests.test_export_clipboard", "ui": "tests.test_ui", "str": "tests.test_stress",
    "prf": "tests.test_performance",
}
MATRIX = {
    "RF01": [("wsp", "WorkspaceTests.test_new_creates_each_type_and_activates"), ("ui", "AppTests.test_welcome_screen_then_new_diagram_opens_tab")],
    "RF02": [("wsp", "WorkspaceTests.test_open_roundtrip_recent_files_and_reuse_of_open_document"), ("ui", "AppTests.test_save_open_recent_and_dirty_marker")],
    "RF03": [("wsp", "WorkspaceTests.test_duplicate_is_independent_and_unsaved"), ("ui", "AppTests.test_duplicate_opens_new_tab")],
    "RF04": [("exp", "Raster.test_export_every_format_and_grid_is_never_exported"), ("ui", "Phase6UiTests.test_export_image_formats_by_extension_and_errors")],
    "RF05": [("exp", "Raster.test_dib_has_bitmapinfoheader_and_matches_size"), ("exp", "Raster.test_command_backend_pipes_png_to_clipboard_tool"), ("ui", "Phase6UiTests.test_copy_to_clipboard_menu_shortcut_toolbar_and_failure")],
    "RF06": [("ui", "AppTests.test_exit_checks_unsaved_then_closes_window")],
    "RF07": [("edm", "Toolbars.test_order_and_shortcuts"), ("ui", "InteractionUiTests.test_toolbar_lists_tools_in_order_for_each_diagram_type")],
    "RF08": [("edm", "Toolbars.test_order_and_shortcuts"), ("ui", "InteractionUiTests.test_clicking_toolbar_and_keyboard_shortcuts_change_tool")],
    "RF09": [("ui", "InteractionUiTests.test_context_menu_lists_toolbar_tools")],
    "RF10": [("ui", "InteractionUiTests.test_tooltips_and_tool_hint_options")],
    "RF11": [("int", "NodeCreation.test_click_creates_snapped_selected_node_and_notifies"), ("ui", "InteractionUiTests.test_mouse_creates_node_respecting_zoom")],
    "RF12": [("ui", "PropertiesUiTests.test_auto_edit_node_opens_panel_only_for_nodes_with_properties")],
    "RF13": [("int", "NodeCreation.test_no_creation_on_top_of_other_node_but_inside_package"), ("val", "NoteConnectorRules.test_connect_node_to_note_and_anchor_from_note")],
    "RF14": [("int", "EdgeCreation.test_note_connector_node_to_note_and_note_to_point"), ("val", "NoteConnectorRules.test_connect_node_to_note_and_anchor_from_note")],
    "RF15": [("int", "ShiftContainment.test_shift_drop_attaches_and_detaches"), ("edm", "Containment.test_attach_and_detach_with_undo"), ("int", "NodeCreation.test_no_creation_on_top_of_other_node_but_inside_package")],
    "RF16": [("int", "EdgeCreation.test_rubber_band_creates_edge_and_overlay_is_temporary"), ("ui", "InteractionUiTests.test_mouse_drag_creates_edge_and_selection_overlay_follows")],
    "RF17": [("rnd", "EdgePaths.test_path_follows_node_movement"), ("rnd", "EdgePaths.test_parallel_and_self_edges_do_not_overlap")],
    "RF18": [("val", "ClassDiagramRules"), ("val", "ObjectDiagramRules"), ("val", "UseCaseRules"), ("val", "StateRules"), ("str", "StressTests")],
    "RF19": [("int", "EdgeCreation.test_self_edge_by_dragging_inside_node_and_blocked_self_inheritance"), ("val", "StateRules.test_transition_limits"), ("val", "UseCaseRules.test_rules")],
    "RF20": [("prp", "EdgeFields.test_class_diagram_edges"), ("prp", "Commit.test_swap_composition_for_aggregation_without_recreating"), ("ui", "PropertiesUiTests.test_edge_panel_swaps_composition_for_aggregation")],
    "RF21": [("edm", "UndoRedo"), ("ui", "AppTests.test_undo_redo_via_app"), ("str", "StressTests")],
    "RF22": [("prp", "NodeFields.test_fields_match_annex_for_every_node_type"), ("ui", "PropertiesUiTests.test_double_click_opens_panel_and_changes_are_undoable"), ("ui", "PropertiesUiTests.test_tab_moves_between_fields_in_a_cycle"), ("ui", "PropertiesUiTests.test_ctrl_enter_and_edit_menu_follow_selection")],
    "RF23": [("prp", "Stereotype"), ("ui", "PropertiesUiTests.test_ctrl_q_inserts_stereotype_without_quitting")],
    "RF24": [("rnd", "Markup"), ("rnd", "SvgOutput.test_well_formed_with_expected_primitives"), ("ui", "PropertiesUiTests.test_italic_and_underline_markup_are_drawn_in_canvas")],
    "RF25": [("val", "ObjectDiagramRules.test_field_only_inside_object"), ("edm", "Persistence.test_invalid_files_rejected"), ("exp", "ElementClipboard.test_lone_field_cannot_be_pasted_but_object_with_fields_can")],
    "RF26": [("val", "ObjectDiagramRules.test_reference_goes_from_field_to_object")],
    "RF27": [("val", "SequenceRules.test_first_call_creates_both_boxes_and_second_root_is_rejected"), ("int", "SequenceInteraction.test_call_constructor_selfcall_and_return_by_dragging")],
    "RF28": [("val", "SequenceRules.test_self_call_and_constructor_call")],
    "RF29": [("rnd", "Layout.test_sequence_layout_order_alignment_and_nesting"), ("val", "SequenceRules.test_self_call_and_constructor_call")],
    "RF30": [("val", "SequenceRules.test_control_flow_jump_fails_silently_and_valid_flow_works"), ("val", "SequenceRules.test_box_cannot_receive_calls_from_several_callers"), ("int", "ConstructorDeletion"), ("str", "StressTests.test_sequence")],
    "RF31": [("prp", "Commit.test_open_bottom_is_boolean"), ("ui", "PropertiesUiTests.test_panel_closes_when_element_disappears_and_follows_undo")],
    "RF32": [("int", "SelectionAndMove.test_click_selects_toggles_and_ctrl_adds"), ("int", "SelectionAndMove.test_lasso_selects_contained_elements_only")],
    "RF33": [("int", "DeletionAndSelectAll.test_delete_selection_and_undo"), ("ui", "InteractionUiTests.test_edit_menu_select_all_and_delete")],
    "RF34": [("exp", "ElementClipboard"), ("ui", "Phase6UiTests.test_cut_copy_paste_between_diagrams_with_compatibility_errors")],
    "RF35": [("int", "DeletionAndSelectAll"), ("ui", "InteractionUiTests.test_drag_node_with_mouse_and_delete_key")],
    "RF36": [("int", "SelectionAndMove.test_drag_moves_with_snap_live_and_is_one_undo_step"), ("ui", "AppTests.test_dark_mode_and_grid_toggle_persist")],
    "RF37": [("wsp", "SettingsAndZoom.test_zoom_two_levels_each_direction"), ("ui", "AppTests.test_zoom_levels_limits_and_scroll_region")],
    "RF38": [("exp", "DiagramSize"), ("ui", "Phase6UiTests.test_diagram_size_dialog_fixed_area_growth_and_defaults")],
    "RF39": [("exp", "FontMetrics"), ("ui", "Phase6UiTests.test_font_change_affects_layout_and_drawing_and_restores")],
    "RF40": [("ui", "AppTests.test_dark_mode_and_grid_toggle_persist"), ("ui", "Phase6UiTests.test_dark_mode_themes_the_whole_interface_and_restores")],
    "RF41": [("edm", "Notifications.test_duration_range_zero_disables_and_expiry"), ("ui", "Phase6UiTests.test_notifications_appear_bottom_left_with_colors_and_expire")],
    "RF42": [("edm", "Notifications.test_duration_range_zero_disables_and_expiry"), ("ui", "Phase6UiTests.test_duration_dialog_range_default_and_persistence"), ("ui", "Phase6UiTests.test_duration_zero_disables_all_notifications")],
    "RNF01": [("exp", "DiagramSize.test_default_follows_screen_and_is_clamped"), ("prf", "Headless"), ("prf", "OnScreen")],
    "RNF02": [("edm", "Persistence.test_round_trip_and_duplicate")],
    "RNF03": [("ui", "AppTests.test_keyboard_shortcuts_are_bound_and_work"), ("ui", "PropertiesUiTests.test_double_click_opens_panel_and_changes_are_undoable"), ("ui", "PropertiesUiTests.test_ctrl_enter_and_edit_menu_follow_selection"), ("ui", "Phase6UiTests.test_copy_to_clipboard_menu_shortcut_toolbar_and_failure")],
}


def resolve(key: str, path: str) -> bool:
    module = importlib.import_module(T[key])
    obj = module
    for part in path.split("."):
        if not hasattr(obj, part):
            return False
        obj = getattr(obj, part)
    return True


def verify() -> list[str]:
    return [f"{rid}: {T[k]}.{p}" for rid, refs in MATRIX.items() for k, p in refs if not resolve(k, p)]


def main() -> int:
    missing = verify()
    if missing:
        print("Referências que não existem:", *missing, sep="\n  ")
        return 1
    lines = ["# Rastreabilidade: requisito → testes\n", "Gerado por `python tools/traceability.py` (falha se algum teste citado não existir).\n",
             "| Requisito | Testes que o verificam |", "|---|---|"]
    for rid, refs in MATRIX.items():
        lines.append(f"| {rid} | " + "<br>".join(f"`{T[k].split('.')[-1]}.{p}`" for k, p in refs) + " |")
    Path(__file__).resolve().parent.parent.joinpath("docs", "RASTREABILIDADE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: {len(MATRIX)} requisitos, {sum(len(r) for r in MATRIX.values())} referências verificadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
