# Export a SketchUp model for plan-to-photo: model.obj (meters, Z up, one object per part,
# smooth normals across soft edges), parts.json (name, size, material, position of every part)
# and scenes.json (the camera of every saved scene, ready for line_drawing.py).
#
# Works in SketchUp desktop (Make 2017 or newer, any Pro). It does not need the Pro OBJ exporter.
# Run it from Window > Ruby Console:
#   load "/path/to/export_for_p2p.rb"
#   P2P.export("/path/to/out")           # or P2P.export with no argument to pick a folder
# Or copy it into the Plugins folder and use Extensions > Export for plan-to-photo.
#
# What it exports: the selection if anything is selected, otherwise everything visible (hidden
# objects and hidden tags are skipped). Pick the scene that shows the assembled piece first, so
# exploded views, dimension notes and scale figures on other tags stay out.
require 'json'

module P2P
  M = 0.0254 # SketchUp's internal unit is the inch

  def self.visible?(e)
    return false if e.respond_to?(:hidden?) && e.hidden?
    l = e.respond_to?(:layer) ? e.layer : nil
    return true unless l
    return false unless l.visible?
    f = l.respond_to?(:folder) ? l.folder : nil
    while f
      return false unless f.visible?
      f = f.respond_to?(:folder) ? f.folder : nil
    end
    true
  end

  def self.instance?(e)
    e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
  end

  def self.defn(e)
    e.is_a?(Sketchup::Group) ? (e.respond_to?(:definition) ? e.definition : e.entities.parent) : e.definition
  end

  def self.label(e, n)
    return e.name unless e.name.to_s.strip.empty?
    d = defn(e)
    return d.name if e.is_a?(Sketchup::ComponentInstance)
    "group #{n}"
  end

  # Normal at vertex v of face f, averaged over the faces reached across soft or smooth edges at v.
  def self.vnormal(f, v)
    seen = { f => true }
    todo = [f]
    until todo.empty?
      g = todo.pop
      g.edges.each do |e|
        next unless e.used_by?(v) && (e.soft? || e.smooth?)
        e.faces.each { |h| next if seen[h]; seen[h] = true; todo << h }
      end
    end
    n = Geom::Vector3d.new(0, 0, 0)
    seen.keys.each { |h| n = n + h.normal }
    n.length > 0 ? n.normalize : f.normal
  end

  # Collect parts: every group or component whose own entities hold faces is one part; loose faces
  # at the top level are one more. Nested instances become parts of their own.
  def self.collect(ents, tr, mat, path, out, counter)
    faces = ents.grep(Sketchup::Face).select { |f| visible?(f) }
    out << { faces: faces, tr: tr, mat: mat, path: path } unless faces.empty?
    ents.each do |e|
      next unless instance?(e) && visible?(e)
      counter[0] += 1
      name = label(e, counter[0])
      collect(defn(e).entities, tr * e.transformation, e.material || mat, path + [name], out, counter)
    end
  end

  def self.mname(m)
    m ? (m.respond_to?(:display_name) ? m.display_name : m.name) : nil
  end

  def self.export(dir = nil)
    model = Sketchup.active_model
    dir ||= (UI.respond_to?(:select_directory) ? UI.select_directory(title: 'Export for plan-to-photo') : File.dirname(model.path))
    return unless dir
    Dir.mkdir(dir) unless File.directory?(dir)
    sel = model.selection.to_a
    top = sel.empty? ? model.entities.to_a : sel
    parts = []
    counter = [0]
    loose = top.grep(Sketchup::Face).select { |f| visible?(f) }
    parts << { faces: loose, tr: Geom::Transformation.new, mat: nil, path: ['loose faces'] } unless loose.empty?
    top.each do |e|
      next unless instance?(e) && visible?(e)
      counter[0] += 1
      collect(defn(e).entities, e.transformation, e.material, [label(e, counter[0])], parts, counter)
    end

    names = Hash.new(0)
    obj = ["# plan-to-photo export from #{File.basename(model.path)}, meters, Z up", 'mtllib none']
    nv = 0
    nn = 0
    info = []
    parts.each do |p|
      base = p[:path].last.gsub(/\s+/, '_')
      names[base] += 1
      oname = names[base] > 1 ? "#{base}.#{names[base]}" : base
      tr = p[:tr]
      lo = [1e9, 1e9, 1e9]
      hi = [-1e9, -1e9, -1e9]
      mats = Hash.new(0)
      obj << "o #{oname}"
      cur = nil
      p[:faces].each do |f|
        m = mname(f.material || p[:mat]) || 'default'
        mats[m] += f.area
        (obj << "usemtl #{m.gsub(/\s+/, '_')}"; cur = m) if m != cur
        mesh = f.mesh(0)
        vn = {}
        f.vertices.each { |v| vn[v] = vnormal(f, v) }
        idx = []
        (1..mesh.count_points).each do |i|
          pt = mesh.point_at(i)
          w = pt.transform(tr)
          c = [w.x * M, w.y * M, w.z * M]
          3.times { |k| lo[k] = c[k] if c[k] < lo[k]; hi[k] = c[k] if c[k] > hi[k] }
          obj << format('v %.5f %.5f %.5f', *c)
          v = f.vertices.find { |x| x.position == pt }
          n = (v ? vn[v] : f.normal).transform(tr)
          n = n.length > 0 ? n.normalize : n
          obj << format('vn %.4f %.4f %.4f', n.x, n.y, n.z)
          nv += 1
          nn += 1
          idx << nv
        end
        mesh.polygons.each do |poly|
          obj << 'f ' + poly.map { |i| j = idx[i.abs - 1]; "#{j}//#{j}" }.join(' ')
        end
      end
      size = (0..2).map { |k| ((hi[k] - lo[k]) / M).round(3) }
      info << { object: oname, path: p[:path].join(' / '), material: mats.max_by { |_, a| a }&.first,
                size_in: size, min_m: lo.map { |x| x.round(4) }, max_m: hi.map { |x| x.round(4) } }
    end
    File.write(File.join(dir, 'model.obj'), obj.join("\n") + "\n")

    view = model.active_view
    vaspect = view.vpwidth.to_f / view.vpheight
    cams = []
    add = lambda do |name, cam|
      aspect = cam.respond_to?(:aspect_ratio) && cam.aspect_ratio > 0 ? cam.aspect_ratio : vaspect
      fov = cam.fov
      by_h = cam.respond_to?(:fov_is_height?) ? cam.fov_is_height? : true
      t = Math.tan(fov * Math::PI / 360)
      h = by_h ? 2 * Math.atan(t * aspect) : fov * Math::PI / 180
      v = by_h ? fov * Math::PI / 180 : 2 * Math.atan(t / aspect)
      h32 = [h, 2 * Math.atan(Math.tan(v / 2) * 1.5)].max # widest 3:2 view that crops nothing
      cams << { name: name, perspective: cam.perspective?,
                eye: cam.eye.to_a.map { |x| (x * M).round(4) }, target: cam.target.to_a.map { |x| (x * M).round(4) },
                up: cam.up.to_a.map { |x| x.round(4) }, hfov_3x2: (h32 * 180 / Math::PI).round(2) }
    end
    add.call('current view', view.camera)
    model.pages.each { |pg| add.call(pg.name, pg.camera) if pg.use_camera? }
    File.write(File.join(dir, 'scenes.json'), JSON.pretty_generate(cams))

    mats = model.materials.map { |m| { name: mname(m), color: m.color.to_a.first(3), texture: m.texture ? File.basename(m.texture.filename) : nil } }
    File.write(File.join(dir, 'parts.json'), JSON.pretty_generate(
      { source: File.basename(model.path), units: 'size_in is inches; min_m/max_m are meters',
        exported: sel.empty? ? 'visible' : 'selection', parts: info, materials: mats }))
    msg = "plan-to-photo: #{info.size} parts, #{cams.size} cameras written to #{dir}"
    puts msg
    msg
  end
end

unless file_loaded?(__FILE__)
  UI.menu('Extensions').add_item('Export for plan-to-photo') { P2P.export }
  file_loaded(__FILE__)
end
