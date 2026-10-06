cask "twine-app" do
  version "0.2.0"
  sha256 "d0f2ac46654333baa32afe208ed4f906f28ba3c6c541705eace0942e5c113dd5"

  url "https://github.com/aravind-n/twine/releases/download/v#{version}/Twine-#{version}-macos-universal.dmg"
  name "Twine"
  desc "Workspace for coordinating coding agents"
  homepage "https://github.com/aravind-n/twine"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: :tahoe

  app "Twine.app"

  # Twine's saved sessions, transcripts, and workflows are user data.
  # No zap stanza required.
end
