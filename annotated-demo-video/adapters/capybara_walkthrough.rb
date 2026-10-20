# Records a walkthrough from inside a Rails/Capybara system test, for apps whose flows need test fixtures,
# sign-in helpers or background jobs that a plain browser script can't reach. Writes the same
# frames/ + manifest.json that record.cjs does, so finish.py builds the MP4 and player from it.
#
#   require Rails.root.join("tmp/walkthrough_skill/adapters/capybara_walkthrough")   # wherever you copied the skill
#
#   class ZzWalkthroughTest < ApplicationSystemTestCase
#     include CapybaraWalkthrough
#     test "walkthrough" do
#       walkthrough_start out: ENV.fetch("WALKTHROUGH_DIR"), title: "Moving a roster", kicker: "Acme · new in this release", steps: 3
#       visit root_path
#       walkthrough_title "Moving a roster", "Three steps from the old tool to ours."
#       walkthrough_frame ".btn.move", "Start here", "The new button sits beside Library.", chapter: "The coach"
#       ...
#       walkthrough_finish
#     end
#   end
#
# Keep the test out of the suite (name it zz_*, run it on its own, delete or skip committing it).
require "json"
require "fileutils"

module CapybaraWalkthrough
  SKILL = File.expand_path("..", __dir__)
  STILL = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}".freeze

  def walkthrough_start(out:, title:, steps:, kicker: "", note: "", width: 1440, height: 900, theme: {})
    @wt = { out: File.expand_path(out), w: width, h: height, steps: steps, n: 0,
            theme: JSON.parse(File.read(File.join(SKILL, "assets/theme.json"))).merge(theme.transform_keys(&:to_s)),
            manifest: { title: title, kicker: kicker, note: note, viewport: { width: width, height: height }, frames: [] } }
    @wt[:manifest][:theme] = @wt[:theme]
    FileUtils.rm_rf(File.join(@wt[:out], "frames"))
    FileUtils.mkdir_p(File.join(@wt[:out], "frames"))
    walkthrough_resize
  end

  def walkthrough_title(title, body = "", kicker: nil)
    walkthrough_inject
    page.execute_script("__wt.titleCard(arguments[0])", { "kicker" => kicker || @wt[:manifest][:kicker], "title" => title, "body" => body, "height" => @wt[:h] })
    walkthrough_shoot(0, "title", title, body, nil)
  end

  # selector: what the caption is about; target: a different element to centre and ring, if any.
  def walkthrough_frame(selector, title, body = "", target: nil, chapter: nil, side: "right")
    walkthrough_inject
    @wt[:n] += 1
    offset = page.evaluate_script("__wt.frame(arguments[0])", { "selector" => selector, "target" => target, "title" => title, "body" => body,
      "count" => "#{@wt[:n]} / #{@wt[:steps]}", "height" => @wt[:h], "side" => side })
    walkthrough_shoot(offset.to_i, "frame", title, body, chapter)
  end

  def walkthrough_finish
    File.write(File.join(@wt[:out], "manifest.json"), JSON.pretty_generate(@wt[:manifest]))
    warn "walkthrough: #{@wt[:n]} frames, but walkthrough_start said steps: #{@wt[:steps]}" if @wt[:n] != @wt[:steps]
  end

  # Call after Capybara.reset_sessions! (signing out) so the window keeps the recording size.
  def walkthrough_resize
    if page.driver.respond_to?(:resize) then page.driver.resize(@wt[:w], @wt[:h])
    else page.current_window.resize_to(@wt[:w], @wt[:h])
    end
  end

  private
    def walkthrough_inject
      page.execute_script("window.__wtTheme = arguments[0]", @wt[:theme])
      page.execute_script(File.read(File.join(SKILL, "scripts/annotate.js")))
      page.execute_script(<<~JS, STILL)
        let s = document.getElementById('wt-still');
        if (!s) { s = document.createElement('style'); s.id = 'wt-still'; document.head.appendChild(s); }
        s.textContent = arguments[0]; window.scrollTo(0, 0);
      JS
    end

    def walkthrough_shoot(offset, kind, title, body, chapter)
      page.evaluate_async_script("__wt.ready().then(() => arguments[0]())")
      sleep 0.2
      file = format("%02d.png", @wt[:manifest][:frames].size)
      path = File.join(@wt[:out], "frames", file)
      begin
        page.driver.save_screenshot(path, full: true) # cuprite / ferrum: full page, cropped later at offset
      rescue ArgumentError
        page.execute_script("window.scrollTo(0, arguments[0])", offset) # selenium: viewport shot at the offset
        page.save_screenshot(path)
        offset = 0
      end
      page.execute_script("window.__wt && __wt.clear()")
      @wt[:manifest][:frames] << { file: file, offset: offset, kind: kind, title: title, body: body, chapter: chapter }
    end
end
