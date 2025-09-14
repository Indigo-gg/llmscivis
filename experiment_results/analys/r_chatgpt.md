差异比较报告
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\cutter.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\cutter_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\cutter.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\cutter_corrt.html
@@ -30,6 +30,7 @@
const vtkColorTransferFunction = vtk.Rendering.Core.vtkColorTransferFunction;
const vtkAxesActor = vtk.Rendering.Core.vtkAxesActor;
const vtkOrientationMarkerWidget = vtk.Interaction.Widgets.vtkOrientationMarkerWidget;
+const vtkXMLImageDataReader = vtk.IO.XML.vtkXMLImageDataReader;

// ----------------------------------------------------------------------------
// Create renderer and render window
@@ -44,7 +45,7 @@
// ----------------------------------------------------------------------------
// Load the rotor.vti dataset from the provided URL
// ----------------------------------------------------------------------------
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: false });
+const reader = vtkXMLImageDataReader.newInstance();
reader.setUrl('http://127.0.0.1:5000/dataset/rotor.vti').then(() => {
reader.loadData().then(() => {
const imageData = reader.getOutputData();

==================================================
差异统计：
  总差异行数: 3
  新增行数: 2
  删除行数: 1
  修改行数: 1
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\isosurface.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\isosurface_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\isosurface.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\isosurface_corrt.html
@@ -31,10 +31,12 @@
const vtkColorTransferFunction = vtk.Rendering.Core.vtkColorTransferFunction;
const vtkPiecewiseFunction = vtk.Common.DataModel.vtkPiecewiseFunction;
const vtkContourFilter = vtk.Filters.General.vtkContourFilter;
+const vtkImageMarchingCubes = vtk.Filters.General.vtkImageMarchingCubes;
const vtkCalculator = vtk.Filters.General.vtkCalculator;
const vtkOrientationMarkerWidget = vtk.Interaction.Widgets.vtkOrientationMarkerWidget;
const vtkAxesActor = vtk.Rendering.Core.vtkAxesActor;

+const vtkXMLImageDataReader = vtk.IO.XML.vtkXMLImageDataReader;
// ----------------------------------------------------------------------------
// Create renderer and render window
// ----------------------------------------------------------------------------
@@ -48,7 +50,7 @@
// ----------------------------------------------------------------------------
// Load the dataset
// ----------------------------------------------------------------------------
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: true });
+const reader = vtkXMLImageDataReader.newInstance();
reader.setUrl('http://127.0.0.1:5000/dataset/deepwater.vti').then(() => {
reader.loadData().then(() => {
const imageData = reader.getOutputData();
@@ -61,49 +63,47 @@
let scalarName = 'prs';

if (arrayNames.includes('v02') && arrayNames.includes('v03')) {
-const calculator = vtkCalculator.newInstance();
-calculator.setInputData(imageData);
-calculator.setFormula({
-getArrays: inputDataSets => ({
-v02: inputDataSets[0].getPointData().getArrayByName('v02'),
-v03: inputDataSets[0].getPointData().getArrayByName('v03'),
-}),
-evaluate: ({ v02, v03 }) => {
-return [Math.sqrt(v02[0] ** 2 + v03[0] ** 2)];
-},
-output: {
+const v02Array = pointData.getArrayByName('v02');
+const v03Array = pointData.getArrayByName('v03');
+if (v02Array && v03Array) {
+const numPoints = imageData.getNumberOfPoints();
+const magnitudeData = new Float64Array(numPoints);
+const v02 = v02Array.getData();
+const v03 = v03Array.getData();
+for (let i = 0; i < numPoints; i++) {
+magnitudeData[i] = Math.sqrt(v02[i] * v02[i] + v03[i] * v03[i]);
+}
+const vtkDataArray = vtk.Common.Core.vtkDataArray;
+const magnitudeVtkArray = vtkDataArray.newInstance({
+numberOfComponents: 1,
+values: magnitudeData,
name: 'velocityMag',
-type: 'Float32Array',
-numberOfComponents: 1,
+});
+pointData.addArray(magnitudeVtkArray);
+pointData.setActiveScalars('velocityMag');
}
-});
-calculator.update();
scalarName = 'velocityMag';
}

// ----------------------------------------------------------------------------
// Create contour filter (isosurface) at mid-value of scalar range
// ----------------------------------------------------------------------------
-const contour = vtkContourFilter.newInstance();
-contour.setInputConnection(reader.getOutputPort());
-contour.setComputeNormals(true);
-contour.setComputeGradients(true);
-contour.setComputeScalars(true);
-contour.setInputArrayToProcess(0, 'Scalars', 'PointData', 'Scalars', scalarName);
-
-// Wait for scalar range to be available
-renderWindow.render(); // Ensure pipeline updates
setTimeout(() => {
const scalars = pointData.getArrayByName(scalarName);
const range = scalars.getRange();
const midValue = (range[0] + range[1]) / 2;
-contour.setValue(0, midValue); // generate isosurface at mid-value
-
+const marchingCubes = vtkImageMarchingCubes.newInstance({
+contourValue: midValue,
+computeNormals: true,
+mergePoints: true,
+});
+marchingCubes.setInputData(imageData);
+renderWindow.render(); // Ensure pipeline updates
// ----------------------------------------------------------------------------
// Create mapper and actor
// ----------------------------------------------------------------------------
const mapper = vtkMapper.newInstance();
-mapper.setInputConnection(contour.getOutputPort());
+mapper.setInputConnection(marchingCubes.getOutputPort());

// Set color mapping: blue → white → red
const lookupTable = vtkColorTransferFunction.newInstance();

==================================================
差异统计：
  总差异行数: 56
  新增行数: 28
  删除行数: 28
  修改行数: 17
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\stream_trancing.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\stream_trancing_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\stream_trancing.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\stream_trancing_corrt.html
@@ -21,15 +21,15 @@
const vtkMapper = vtk.Rendering.Core.vtkMapper;
const vtkOutlineFilter = vtk.Filters.General.vtkOutlineFilter;
const vtkStreamTracer = vtk.Filters.General.vtkStreamTracer;
+const vtkImageStreamline = vtk.Filters.General.vtkImageStreamline;
const vtkPointSource = vtk.Filters.Sources.vtkPointSource;
const vtkTubeFilter = vtk.Filters.General.vtkTubeFilter;

+const vtkXMLImageDataReader=vtk.IO.XML.vtkXMLImageDataReader;
// ----------------------------------------------------------------------------
// Create renderer, render window, and interactor
// ----------------------------------------------------------------------------
const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({
-rootContainer: document.body,
-containerStyle: { height: '100%', width: '100%', position: 'absolute' },
background: [0.1, 0.1, 0.1],
});
const renderer = fullScreenRenderer.getRenderer();
@@ -38,7 +38,7 @@
// ----------------------------------------------------------------------------
// Load the Isabel dataset from the given URL
// ----------------------------------------------------------------------------
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: true });
+const reader=vtkXMLImageDataReader.newInstance()
reader.setUrl('http://127.0.0.1:5000/dataset/isabel.vti').then(() => {
reader.loadData().then(() => {
const imageData = reader.getOutputData();
@@ -70,15 +70,10 @@
// ----------------------------------------------------------------------------
// Compute streamlines using vtkStreamTracer
// ----------------------------------------------------------------------------
-const streamTracer = vtkStreamTracer.newInstance({
-inputConnection: reader.getOutputPort(),
-seedConnection: pointSource.getOutputPort(),
-maximumPropagation: 500,
-initialIntegrationStep: 0.5,
-integrationDirection: 2, // Forward and backward
-});
-streamTracer.setInputArrayToProcess(0, 'Velocity', 'PointData', 'Velocity');
-
+const streamline = vtkImageStreamline.newInstance();
+streamline.setInputData(imageData);
+streamline.setInputConnection(pointSource.getOutputPort(), 1); // 种子点数据
+streamline.set({maximumNumberOfSteps: 1000,integrationStep: 0.5});
// ----------------------------------------------------------------------------
// Enhance streamline appearance with vtkTubeFilter
// ----------------------------------------------------------------------------
@@ -87,7 +82,7 @@
radius: 0.5,
varyRadius: 'VARY_RADIUS_OFF',
});
-tubeFilter.setInputConnection(streamTracer.getOutputPort());
+tubeFilter.setInputConnection(streamline.getOutputPort());

const streamlineMapper = vtkMapper.newInstance();
streamlineMapper.setInputConnection(tubeFilter.getOutputPort());

==================================================
差异统计：
  总差异行数: 21
  新增行数: 8
  删除行数: 13
  修改行数: 6
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\volume_rendering.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\volume_rendering_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\volume_rendering.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\chatgpt-4o\volume_rendering_corrt.html
@@ -30,6 +30,7 @@
const vtkPiecewiseFunction = vtk.Common.DataModel.vtkPiecewiseFunction;
const vtkDataArray = vtk.Common.Core.vtkDataArray;

+const vtkXMLImageDataReader= vtk.IO.XML.vtkXMLImageDataReader;
// ----------------------------------------------------------------------------
// 1. Create renderer and render window
// ----------------------------------------------------------------------------
@@ -43,7 +44,7 @@
// ----------------------------------------------------------------------------
// 2. Load the VTI dataset from the specified URL
// ----------------------------------------------------------------------------
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: true });
+const reader=vtkXMLImageDataReader.newInstance()
reader.setUrl('http://127.0.0.1:5000/dataset/redsea.vti').then(() => {
reader.loadData().then(() => {
const data = reader.getOutputData();

==================================================
差异统计：
  总差异行数: 3
  新增行数: 2
  删除行数: 1
  修改行数: 1
==================================================
