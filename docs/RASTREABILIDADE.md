# Rastreabilidade: requisito → testes

Gerado por `python tools/traceability.py` (falha se algum teste citado não existir).

| Requisito | Testes que o verificam |
|---|---|
| RF01 | `test_workspace.WorkspaceTests.test_new_creates_each_type_and_activates`<br>`test_ui.AppTests.test_welcome_screen_then_new_diagram_opens_tab` |
| RF02 | `test_workspace.WorkspaceTests.test_open_roundtrip_recent_files_and_reuse_of_open_document`<br>`test_ui.AppTests.test_save_open_recent_and_dirty_marker` |
| RF03 | `test_workspace.WorkspaceTests.test_duplicate_is_independent_and_unsaved`<br>`test_ui.AppTests.test_duplicate_opens_new_tab` |
| RF04 | `test_export_clipboard.Raster.test_export_every_format_and_grid_is_never_exported`<br>`test_ui.Phase6UiTests.test_export_image_formats_by_extension_and_errors` |
| RF05 | `test_export_clipboard.Raster.test_dib_has_bitmapinfoheader_and_matches_size`<br>`test_export_clipboard.Raster.test_command_backend_pipes_png_to_clipboard_tool`<br>`test_ui.Phase6UiTests.test_copy_to_clipboard_menu_shortcut_toolbar_and_failure` |
| RF06 | `test_ui.AppTests.test_exit_checks_unsaved_then_closes_window` |
| RF07 | `test_editor_model.Toolbars.test_order_and_shortcuts`<br>`test_ui.InteractionUiTests.test_toolbar_lists_tools_in_order_for_each_diagram_type` |
| RF08 | `test_editor_model.Toolbars.test_order_and_shortcuts`<br>`test_ui.InteractionUiTests.test_clicking_toolbar_and_keyboard_shortcuts_change_tool` |
| RF09 | `test_ui.InteractionUiTests.test_context_menu_lists_toolbar_tools` |
| RF10 | `test_ui.InteractionUiTests.test_tooltips_and_tool_hint_options` |
| RF11 | `test_interaction.NodeCreation.test_click_creates_snapped_selected_node_and_notifies`<br>`test_ui.InteractionUiTests.test_mouse_creates_node_respecting_zoom` |
| RF12 | `test_ui.PropertiesUiTests.test_auto_edit_node_opens_panel_only_for_nodes_with_properties` |
| RF13 | `test_interaction.NodeCreation.test_no_creation_on_top_of_other_node_but_inside_package`<br>`test_validation.NoteConnectorRules.test_connect_node_to_note_and_anchor_from_note` |
| RF14 | `test_interaction.EdgeCreation.test_note_connector_node_to_note_and_note_to_point`<br>`test_validation.NoteConnectorRules.test_connect_node_to_note_and_anchor_from_note` |
| RF15 | `test_interaction.ShiftContainment.test_shift_drop_attaches_and_detaches`<br>`test_editor_model.Containment.test_attach_and_detach_with_undo`<br>`test_interaction.NodeCreation.test_no_creation_on_top_of_other_node_but_inside_package` |
| RF16 | `test_interaction.EdgeCreation.test_rubber_band_creates_edge_and_overlay_is_temporary`<br>`test_ui.InteractionUiTests.test_mouse_drag_creates_edge_and_selection_overlay_follows` |
| RF17 | `test_rendering.EdgePaths.test_path_follows_node_movement`<br>`test_rendering.EdgePaths.test_parallel_and_self_edges_do_not_overlap` |
| RF18 | `test_validation.ClassDiagramRules`<br>`test_validation.ObjectDiagramRules`<br>`test_validation.UseCaseRules`<br>`test_validation.StateRules`<br>`test_stress.StressTests` |
| RF19 | `test_interaction.EdgeCreation.test_self_edge_by_dragging_inside_node_and_blocked_self_inheritance`<br>`test_validation.StateRules.test_transition_limits`<br>`test_validation.UseCaseRules.test_rules` |
| RF20 | `test_properties.EdgeFields.test_class_diagram_edges`<br>`test_properties.Commit.test_swap_composition_for_aggregation_without_recreating`<br>`test_ui.PropertiesUiTests.test_edge_panel_swaps_composition_for_aggregation` |
| RF21 | `test_editor_model.UndoRedo`<br>`test_ui.AppTests.test_undo_redo_via_app`<br>`test_stress.StressTests` |
| RF22 | `test_properties.NodeFields.test_fields_match_annex_for_every_node_type`<br>`test_ui.PropertiesUiTests.test_double_click_opens_panel_and_changes_are_undoable`<br>`test_ui.PropertiesUiTests.test_tab_moves_between_fields_in_a_cycle`<br>`test_ui.PropertiesUiTests.test_ctrl_enter_and_edit_menu_follow_selection` |
| RF23 | `test_properties.Stereotype`<br>`test_ui.PropertiesUiTests.test_ctrl_q_inserts_stereotype_without_quitting` |
| RF24 | `test_rendering.Markup`<br>`test_rendering.SvgOutput.test_well_formed_with_expected_primitives`<br>`test_ui.PropertiesUiTests.test_italic_and_underline_markup_are_drawn_in_canvas` |
| RF25 | `test_validation.ObjectDiagramRules.test_field_only_inside_object`<br>`test_editor_model.Persistence.test_invalid_files_rejected`<br>`test_export_clipboard.ElementClipboard.test_lone_field_cannot_be_pasted_but_object_with_fields_can` |
| RF26 | `test_validation.ObjectDiagramRules.test_reference_goes_from_field_to_object` |
| RF27 | `test_validation.SequenceRules.test_first_call_creates_both_boxes_and_second_root_is_rejected`<br>`test_interaction.SequenceInteraction.test_call_constructor_selfcall_and_return_by_dragging` |
| RF28 | `test_validation.SequenceRules.test_self_call_and_constructor_call` |
| RF29 | `test_rendering.Layout.test_sequence_layout_order_alignment_and_nesting`<br>`test_validation.SequenceRules.test_self_call_and_constructor_call` |
| RF30 | `test_validation.SequenceRules.test_control_flow_jump_fails_silently_and_valid_flow_works`<br>`test_validation.SequenceRules.test_box_cannot_receive_calls_from_several_callers`<br>`test_interaction.ConstructorDeletion`<br>`test_stress.StressTests.test_sequence` |
| RF31 | `test_properties.Commit.test_open_bottom_is_boolean`<br>`test_ui.PropertiesUiTests.test_panel_closes_when_element_disappears_and_follows_undo` |
| RF32 | `test_interaction.SelectionAndMove.test_click_selects_toggles_and_ctrl_adds`<br>`test_interaction.SelectionAndMove.test_lasso_selects_contained_elements_only` |
| RF33 | `test_interaction.DeletionAndSelectAll.test_delete_selection_and_undo`<br>`test_ui.InteractionUiTests.test_edit_menu_select_all_and_delete` |
| RF34 | `test_export_clipboard.ElementClipboard`<br>`test_ui.Phase6UiTests.test_cut_copy_paste_between_diagrams_with_compatibility_errors` |
| RF35 | `test_interaction.DeletionAndSelectAll`<br>`test_ui.InteractionUiTests.test_drag_node_with_mouse_and_delete_key` |
| RF36 | `test_interaction.SelectionAndMove.test_drag_moves_with_snap_live_and_is_one_undo_step`<br>`test_ui.AppTests.test_dark_mode_and_grid_toggle_persist` |
| RF37 | `test_workspace.SettingsAndZoom.test_zoom_two_levels_each_direction`<br>`test_ui.AppTests.test_zoom_levels_limits_and_scroll_region` |
| RF38 | `test_export_clipboard.DiagramSize`<br>`test_ui.Phase6UiTests.test_diagram_size_dialog_fixed_area_growth_and_defaults` |
| RF39 | `test_export_clipboard.FontMetrics`<br>`test_ui.Phase6UiTests.test_font_change_affects_layout_and_drawing_and_restores` |
| RF40 | `test_ui.AppTests.test_dark_mode_and_grid_toggle_persist`<br>`test_ui.Phase6UiTests.test_dark_mode_themes_the_whole_interface_and_restores` |
| RF41 | `test_editor_model.Notifications.test_duration_range_zero_disables_and_expiry`<br>`test_ui.Phase6UiTests.test_notifications_appear_bottom_left_with_colors_and_expire` |
| RF42 | `test_editor_model.Notifications.test_duration_range_zero_disables_and_expiry`<br>`test_ui.Phase6UiTests.test_duration_dialog_range_default_and_persistence`<br>`test_ui.Phase6UiTests.test_duration_zero_disables_all_notifications` |
| RNF01 | `test_export_clipboard.DiagramSize.test_default_follows_screen_and_is_clamped`<br>`test_performance.Headless`<br>`test_performance.OnScreen` |
| RNF02 | `test_editor_model.Persistence.test_round_trip_and_duplicate` |
| RNF03 | `test_ui.AppTests.test_keyboard_shortcuts_are_bound_and_work`<br>`test_ui.PropertiesUiTests.test_double_click_opens_panel_and_changes_are_undoable`<br>`test_ui.PropertiesUiTests.test_ctrl_enter_and_edit_menu_follow_selection`<br>`test_ui.Phase6UiTests.test_copy_to_clipboard_menu_shortcut_toolbar_and_failure` |
