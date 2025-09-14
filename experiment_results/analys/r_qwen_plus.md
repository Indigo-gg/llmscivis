差异比较报告
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\cutter.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\cutter_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\cutter.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\cutter_corrt.html
@@ -21,11 +21,11 @@
const vtkHttpDataSetReader = vtk.IO.Core.vtkHttpDataSetReader;
const vtkImageMapper = vtk.Rendering.Core.vtkImageMapper;
const vtkImageSlice = vtk.Rendering.Core.vtkImageSlice;
-const vtkPiecewiseFunction = vtk.Common.Core.vtkPiecewiseFunction;
-const vtkColorTransferFunction = vtk.Common.Core.vtkColorTransferFunction;
-const vtkImageReslice = vtk.Filters.General.vtkImageReslice;
+const vtkPiecewiseFunction = vtk.Common.DataModel.vtkPiecewiseFunction;// todo
+const vtkColorTransferFunction = vtk.Rendering.Core.vtkColorTransferFunction;
const vtkOrientationMarkerWidget = vtk.Interaction.Widgets.vtkOrientationMarkerWidget;
const vtkAnnotatedCubeActor = vtk.Rendering.Core.vtkAnnotatedCubeActor;
+const vtkXMLImageDataReader = vtk.IO.XML.vtkXMLImageDataReader;

// ----------------------------------------------------------------------------
// Create the render window and renderer
@@ -37,7 +37,7 @@
// ----------------------------------------------------------------------------
// Load the dataset from the specified URL
// ----------------------------------------------------------------------------
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: true });
+const reader = vtkXMLImageDataReader.newInstance({ fetchGzip: false });// todo第一处：使用vtkXMLImageDataReader读取数据集
reader.setUrl('http://127.0.0.1:5000/dataset/rotor.vti').then(() => {
reader.loadData().then(() => {
const imageData = reader.getOutputData();
@@ -45,7 +45,7 @@
// ----------------------------------------------------------------------------
// Set the active scalar array to "Pressure"
// ----------------------------------------------------------------------------
-imageData.setActiveScalars('Pressure');
+imageData.getPointData().setActiveScalars('Pressure');

// ----------------------------------------------------------------------------
// Apply a slice along the Y axis at 80% depth
@@ -54,38 +54,30 @@
const dims = imageData.getDimensions();
const ySliceIndex = Math.floor(dims[1] * 0.8); // 80% of Y dimension

-const reslice = vtkImageReslice.newInstance();
-reslice.setInputData(imageData);
-reslice.setResliceAxesDirectionCosines([1, 0, 0], [0, 0, 1], [0, 1, 0]); // Ensure proper orientation
-reslice.setResliceAxesOrigin(0, ySliceIndex, 0);
-reslice.setOutputDimensionality(2); // Slice is 2D
-reslice.update();
-
-const sliceImageData = reslice.getOutputData();
-
// ----------------------------------------------------------------------------
// Set up mapper and actor for the slice
// ----------------------------------------------------------------------------
-const mapper = vtkImageMapper.newInstance();
-mapper.setInputData(sliceImageData);
-mapper.setScalarVisibility(true);
-mapper.setColorWindow(255); // default
-mapper.setColorLevel(127.5); // default
+const mapper = vtkImageMapper.newInstance();// todo3
+mapper.setInputData(imageData); // 修改：直接输入原始三维数据// todo
+mapper.setSlicingMode(1); //(0:X, 1:Y, 2:Z)
+mapper.setSlice(ySliceIndex); // 新增：设置切片位置

const actor = vtkImageSlice.newInstance();
actor.setMapper(mapper);
+actor.getProperty().setColorWindow(255);// todo4
+actor.getProperty().setColorLevel(127.5);

// ----------------------------------------------------------------------------
// Configure the color map: blue → white → red
// Use full scalar range from the data
// ----------------------------------------------------------------------------
-const scalarRange = sliceImageData.getPointData().getScalars().getRange();
+const scalarRange = imageData.getPointData().getScalars().getRange();// todo3
const ctf = vtkColorTransferFunction.newInstance();
ctf.addRGBPoint(scalarRange[0], 0, 0, 1); // blue
ctf.addRGBPoint((scalarRange[0] + scalarRange[1]) / 2, 1, 1, 1); // white
ctf.addRGBPoint(scalarRange[1], 1, 0, 0); // red

-mapper.setLookupTable(ctf);
+actor.getProperty().setRGBTransferFunction(0, ctf);// todo6

// ----------------------------------------------------------------------------
// Set opacity to fully opaque (no transparency variation)
@@ -93,7 +85,8 @@
const ofun = vtkPiecewiseFunction.newInstance();
ofun.addPoint(0, 1.0);
ofun.addPoint(255, 1.0);
-actor.getProperty().setScalarOpacity(ofun);
+actor.getProperty().setScalarOpacity(0, ofun);
+actor.getProperty().setUseLookupTableScalarRange(true); // todo明确设置使用查找表标量范围

// ----------------------------------------------------------------------------
// Add actor to renderer
@@ -106,9 +99,12 @@
const cubeActor = vtkAnnotatedCubeActor.newInstance();
const orientationWidget = vtkOrientationMarkerWidget.newInstance({
actor: cubeActor,
-interactor: fullScreenRenderer.getInteractor()
-});
-orientationWidget.setViewport(0.8, 0.0, 1.0, 0.2); // bottom-right corner
+}); // 移除在 newInstance() 调用中设置 interactor// todo5
+orientationWidget.setInteractor(fullScreenRenderer.getInteractor());
+orientationWidget.setViewportCorner(
+vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.BOTTOM_RIGHT
+);
+orientationWidget.setViewportSize(0.2); // 例如，将视口大小设置为渲染窗口的20%
orientationWidget.setMinPixelSize(100);
orientationWidget.setMaxPixelSize(200);
orientationWidget.setEnabled(true);

==================================================
差异统计：
  总差异行数: 46
  新增行数: 21
  删除行数: 25
  修改行数: 14
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\isosurface.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\isosurface_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\isosurface.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\isosurface_corrt.html
@@ -27,19 +27,26 @@
const vtkOrientationMarkerWidget = vtk.Interaction.Widgets.vtkOrientationMarkerWidget;
const vtkAnnotatedCubeActor = vtk.Rendering.Core.vtkAnnotatedCubeActor;

+const vtkXMLImageDataReader = vtk.IO.XML.vtkXMLImageDataReader;
+// const vtkContourFilter = vtk.Filters.General.vtkContourFilter;
+const vtkContourFilter = vtk.Filters.General.vtkContourFilter;
+const vtkImageMarchingCubes = vtk.Filters.General.vtkImageMarchingCubes;
// Create full screen render window
-const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance();
-const renderer = fullScreenRenderer.getRenderer();
+const fullScreenRenderWindow = vtkFullScreenRenderWindow.newInstance(
+{
+backgroundColor: [0, 0, 0],
+}
+);
const renderWindow = fullScreenRenderWindow.getRenderWindow();
+const renderer = fullScreenRenderWindow.getRenderer();
+const reader = vtkXMLImageDataReader.newInstance();

-// Load dataset from the given URL
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: false });
reader.setUrl('http://127.0.0.1:5000/dataset/deepwater.vti').then(() => {
reader.loadData().then(() => {
-const dataset = reader.getOutputData();
+const dataset = reader.getOutputData(0);

// Compute velocity magnitude from v02 and v03 if available
-let scalarName = 'prs'; // default scalar
+let scalarName = 'velocityMagnitude';
const v02 = dataset.getPointData().getArrayByName('v02');
const v03 = dataset.getPointData().getArrayByName('v03');
if (v02 && v03) {
@@ -51,33 +58,45 @@
vMagData[i] = Math.sqrt(v2[0] * v2[0] + v3[0] * v3[0]);
}
const vMagArray = vtkDataArray.newInstance({
-name: 'VelocityMagnitude',
+name: 'velocityMagnitude',
values: vMagData,
numberOfComponents: 1,
});
dataset.getPointData().addArray(vMagArray);
-scalarName = 'VelocityMagnitude';
+scalarName = 'velocityMagnitude';
}
+dataset.getPointData().setActiveScalars('velocityMagnitude');

// Get scalar range
const scalarRange = dataset.getPointData().getArrayByName(scalarName).getRange();
-const isoValue = (scalarRange[0] + scalarRange[1]) / 2;
+console.log(scalarRange);
+const isoValue = scalarRange[0] + 0.5 * (scalarRange[1] - scalarRange[0]);

// Create isosurface filter
-const contour = vtk.Filters.General.vtkContourFilter.newInstance();
-contour.setInputData(dataset);
-contour.setNumberOfContours(1);
-contour.setValue(0, isoValue);
+const marchingCube = vtkImageMarchingCubes.newInstance({
+contourValue: isoValue,
+computeNormals: true,
+mergePoints: true,
+});
+marchingCube.setInputData(dataset);

// Create mapper and actor
const mapper = vtkMapper.newInstance();
-mapper.setInputConnection(contour.getOutputPort());
+// mapper.setInputConnection(contour.getOutputPort());
+mapper.setInputConnection(marchingCube.getOutputPort());
+console.log(marchingCube.getOutputPort());
+// console.log(marchingCube.getOutput());
mapper.setScalarModeToUsePointData();
-mapper.selectColorArray(scalarName);
mapper.setScalarVisibility(true);
-mapper.useLookupTableScalarRangeOn();
-mapper.setLookupTable(vtkColorTransferFunction.newInstance());
-mapper.update();
+mapper.setColorByArrayName('velocityMagnitude');
+const ctf = vtkColorTransferFunction.newInstance();
+mapper.setLookupTable(ctf);
+ctf.setMappingRange(scalarRange[0], scalarRange[1]);
+ctf.addRGBPoint(scalarRange[0], 0, 0, 1);
+ctf.addRGBPoint((scalarRange[0] + scalarRange[1]) / 2, 1, 1, 1);
+ctf.addRGBPoint(scalarRange[1], 1, 0, 0);
+ctf.build();
+mapper.setScalarRange(scalarRange[0], scalarRange[1]);

const actor = vtkActor.newInstance();
actor.setMapper(mapper);
@@ -85,27 +104,13 @@
actor.getProperty().setInterpolationToPhong(); // Smooth shading

// Set up color map: blue → white → red
-const ctf = mapper.getLookupTable();
-ctf.setMappingRange(scalarRange[0], scalarRange[1]);
-ctf.addRGBPoint(scalarRange[0], 0, 0, 1); // blue
-ctf.addRGBPoint((scalarRange[0] + scalarRange[1]) / 2, 1, 1, 1); // white
-ctf.addRGBPoint(scalarRange[1], 1, 0, 0); // red
-ctf.build();

// Add actor to renderer
renderer.addActor(actor);
renderer.resetCamera();
renderWindow.render();

-// Add orientation marker
-const cubeActor = vtkAnnotatedCubeActor.newInstance();
-const orientationWidget = vtkOrientationMarkerWidget.newInstance({
-actor: cubeActor,
-interactor: fullScreenRenderer.getInteractor(),
-});
-orientationWidget.setInteractor(fullScreenRenderer.getInteractor());
-orientationWidget.setEnabled(true);
-orientationWidget.setOrigin(0.8, 0.05); // Bottom-right corner
+renderWindow.getInteractor().start();
});
});
</script>

==================================================
差异统计：
  总差异行数: 71
  新增行数: 38
  删除行数: 33
  修改行数: 16
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\streamtracing.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\streamtracing_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\streamtracing.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\streamtracing_corrt.html
@@ -17,8 +17,9 @@
// Import required VTK.js modules
const vtkFullScreenRenderWindow = vtk.Rendering.Misc.vtkFullScreenRenderWindow;
const vtkHttpDataSetReader = vtk.IO.Core.vtkHttpDataSetReader;
-const vtkStreamTracer = vtk.Filters.HyperStreamline.vtkStreamTracer;
+const vtkImageStreamline = vtk.Filters.General.vtkImageStreamline;
const vtkPolyDataMapper = vtk.Rendering.Core.vtkPolyDataMapper;
+const vtkMapper = vtk.Rendering.Core.vtkMapper;
const vtkActor = vtk.Rendering.Core.vtkActor;
const vtkOutlineFilter = vtk.Filters.General.vtkOutlineFilter;
const vtkPlaneSource = vtk.Filters.Sources.vtkPlaneSource;
@@ -29,9 +30,17 @@
const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({ background: [0, 0, 0] });
const renderer = fullScreenRenderer.getRenderer();
const renderWindow = fullScreenRenderer.getRenderWindow();
-
+const vtkXMLImageDataReader = vtk.IO.XML.vtkXMLImageDataReader;
+function addRepresentation(name, filter, props = {}) {
+const mapper = vtkMapper.newInstance();
+mapper.setInputConnection(filter.getOutputPort());
+const actor = vtkActor.newInstance();
+actor.setMapper(mapper);
+actor.getProperty().set(props);
+renderer.addActor(actor);
+}
// Load the dataset from the given URL
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: true });
+const reader = vtkXMLImageDataReader.newInstance({ fetchGzip: false });
reader.setUrl('http://127.0.0.1:5000/dataset/isabel.vti').then(() => {
reader.update();

@@ -51,54 +60,36 @@
(bounds[4] + bounds[5]) / 2
];

-const seedSource = vtkPlaneSource.newInstance();
-seedSource.setOrigin(center[0] - 20, center[1] - 20, center[2]);
-seedSource.setPoint1(center[0] + 20, center[1] - 20, center[2]);
-seedSource.setPoint2(center[0] - 20, center[1] + 20, center[2]);
-seedSource.setXResolution(10);
-seedSource.setYResolution(10);
-seedSource.update();
-
-// 3. Compute streamlines following the velocity field
-const streamTracer = vtkStreamTracer.newInstance({
-integratorType: 5, // RUNGE_KUTTA_45
-maximumNumberOfSteps: 2000,
-stepLength: 0.25,
-startStepLength: 0.01,
-minStepLength: 0.001,
-maxStepLength: 1.0,
-terminalSpeed: 1e-12,
-integrationDirection: 2, // BOTH
+const pointSource = vtk.Filters.Sources.vtkPointSource.newInstance();
+pointSource.setNumberOfPoints(1000);  // 增加种子点密度
+pointSource.setCenter(
+(bounds[0] + bounds[1]) / 2,
+(bounds[2] + bounds[3]) / 2,
+(bounds[4] + bounds[5]) / 2
+);
+pointSource.setRadius(Math.max(
+bounds[1] - bounds[0],
+bounds[3] - bounds[2],
+bounds[5] - bounds[4],
+) / 2);
+const streamline = vtkImageStreamline.newInstance();
+streamline.setInputData(dataset);
+streamline.setInputConnection(pointSource.getOutputPort(), 1); // 种子点数据
+streamline.set({
+maximumNumberOfSteps: 1000,
+integrationStep: 0.5,
});
-streamTracer.setInputData(dataset);
-streamTracer.setSourceConnection(seedSource.getOutputPort());
-streamTracer.update();
-
-// 4. Render streamlines in cyan [0, 1, 1] with specified line width
-const streamlineMapper = vtkPolyDataMapper.newInstance();
-streamlineMapper.setInputConnection(streamTracer.getOutputPort());
-
-const streamlineActor = vtkActor.newInstance();
-streamlineActor.setMapper(streamlineMapper);
-streamlineActor.getProperty().setColor(0, 1, 1); // Cyan
-streamlineActor.getProperty().setLineWidth(2);   // Line width 2
-
-// 5. Render dataset outline in red [1, 0, 0] with specified line width
+addRepresentation('streamLine', streamline, {
+diffuseColor: [0, 1, 1], // 使用 diffuseColor
+lineWidth: 5,            // 使用更粗的线条
+});
const outlineFilter = vtkOutlineFilter.newInstance();
-outlineFilter.setInputData(dataset);
-outlineFilter.update();
-
-const outlineMapper = vtkPolyDataMapper.newInstance();
-outlineMapper.setInputConnection(outlineFilter.getOutputPort());
-
-const outlineActor = vtkActor.newInstance();
-outlineActor.setMapper(outlineMapper);
-outlineActor.getProperty().setColor(1, 0, 0); // Red
-outlineActor.getProperty().setLineWidth(2);   // Line width 2
-
+outlineFilter.setInputData(dataset); // 使用统一的变量名
+addRepresentation('outline', outlineFilter, {
+diffuseColor: [1, 0, 0], // 使用 diffuseColor
+lineWidth: 3,            // 使用更粗的线条
+});
// Add actors to the renderer
-renderer.addActor(streamlineActor);
-renderer.addActor(outlineActor);

// Reset camera and render
renderer.resetCamera();

==================================================
差异统计：
  总差异行数: 87
  新增行数: 39
  删除行数: 48
  修改行数: 30
==================================================
正在比较文件：D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\volume_rendering.html 和 D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\volume_rendering_corrt.html
--- D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\volume_rendering.html
+++ D:\Pcode\LLM4VIS\llmscivis\experiment_results\generated_code\qwen_plus\volume_rendering_corrt.html
@@ -25,14 +25,15 @@
const vtkVolume = vtk.Rendering.Core.vtkVolume;
const vtkVolumeMapper = vtk.Rendering.Core.vtkVolumeMapper;
const vtkVolumeProperty = vtk.Rendering.Core.vtkVolumeProperty;
+const vtkXMLImageDataReader = vtk.IO.XML.vtkXMLImageDataReader;

// Create full screen render window
const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({ background: [0, 0, 0] });
const renderer = fullScreenRenderer.getRenderer();
-const renderWindow = fullScreenRenderWindow.getRenderWindow();
+const renderWindow = fullScreenRenderer.getRenderWindow();

// Load dataset from the given URL
-const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: false });
+const reader = vtkXMLImageDataReader.newInstance({ fetchGzip: false });
reader.setUrl('http://127.0.0.1:5000/dataset/redsea.vti').then(() => {
reader.loadData().then(() => {
const dataset = reader.getOutputData();
@@ -59,11 +60,12 @@
// Add to dataset and set as active scalar
dataset.getPointData().addArray(magnitude);
dataset.getPointData().setActiveScalars('VelocityMagnitude');
+console.log(dataset.toJSON())

// Setup volume mapper
const volumeMapper = vtkVolumeMapper.newInstance();
volumeMapper.setInputData(dataset);
-volumeMapper.setSampleDistance(0.5); // Adjust for quality/performance
+volumeMapper.setSampleDistance(0.1); // Adjust for quality/performance

// Setup color transfer function (blue -> white -> red)
const colorTransferFunction = vtkColorTransferFunction.newInstance();
@@ -84,8 +86,6 @@

// Setup volume property
const volumeProperty = vtkVolumeProperty.newInstance();
-volumeProperty.setColor(colorTransferFunction);
-volumeProperty.setScalarOpacity(opacityFunction);
volumeProperty.setInterpolationTypeToLinear();
volumeProperty.setAmbient(0.2);
volumeProperty.setDiffuse(0.9);
@@ -96,6 +96,10 @@
const volume = vtkVolume.newInstance();
volume.setMapper(volumeMapper);
volume.setProperty(volumeProperty);
+volume.getProperty().setRGBTransferFunction(0, colorTransferFunction);
+volume.getProperty().setScalarOpacityUnitDistance(0, 0.1);
+volume.getProperty().setShade(false);
+volume.getProperty().setScalarOpacity(0, opacityFunction);

// Add volume to scene
renderer.addActor(volume);
@@ -107,9 +111,9 @@
(bounds[2] + bounds[3]) / 2,
(bounds[4] + bounds[5]) / 2
];
-renderer.getCamera().setFocalPoint(...center);
-renderer.getCamera().setPosition(center[0], center[1], center[2] - 100); // Look along +Z
-renderer.getCamera().setViewUp(0, 1, 0);
+renderer.getActiveCamera().setFocalPoint(...center);
+renderer.getActiveCamera().setPosition(center[0], center[1], center[2] + 10); // Look along +Z
+renderer.getActiveCamera().setViewUp(0, 1, 0);
renderer.resetCamera();
renderWindow.render();
});

==================================================
差异统计：
  总差异行数: 20
  新增行数: 12
  删除行数: 8
  修改行数: 6
==================================================
